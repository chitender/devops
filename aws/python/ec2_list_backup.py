import boto3
import time
import sys, getopt
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import dateutil.parser
import xlsxwriter
import smtplib, ssl
from os.path import basename
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes

#### Config ########

AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""
AWS_SESSION_TOKEN = ""
REGION_NAME = "ap-south-1"
smtp_server = "" #### SMTP Server host endpoint
port = 587  # For SSL
sender_email = ""  # Enter your address
receiver_email = ""  # Enter receiver address
password = ""

#### Config End #######

#### Mail Content ###
mail_content = '''Hello,
find attached the Backup report.
Thank You
'''
#### Mail Content End ###

amiCount = 0 # initialising the variable for ami created in last 24Hours

##### Creating session with AWS
session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY,region_name=REGION_NAME, aws_session_token=AWS_SESSION_TOKEN )
##### Getting AWS Account ID ######
accountId = session.client('sts').get_caller_identity().get('Account')

ec2 = session.resource('ec2')
#### getting instance list
instanceCount = ec2.instances.all()

#### getting instance which match filter Excludebackup: False
instanceAvailableBackup = ec2.instances.filter(Filters=[{'Name': 'tag:ExcludeBackup', 'Values':['False']}])

availableInstanceCount = len([instance for instance in instanceCount ])
availableInstanceCountForBackup = len([instance for instance in instanceAvailableBackup ])

ec2_client = session.client('ec2')

####### Getting list of Ami
imagesList = ec2_client.describe_images(Owners=['self'])
print(len(imagesList['Images']))
for ami in imagesList['Images']:
    # getDate = ami['CreationDate'].split("T")
    amiCreatedDate = dateutil.parser.isoparse(ami['CreationDate'])
    naive = amiCreatedDate.replace(tzinfo=None)
    print (ami['ImageId'],amiCreatedDate)
    difference = datetime.utcnow() - naive
    if difference.days == 0:
        print ("Ami created in last 24 hours")
        amiCount = amiCount + 1
##### Calculating Missing Ami count
amiMissingCount = amiCount - availableInstanceCountForBackup
print("total instance:", availableInstanceCount)
print("instance available for backup:", availableInstanceCountForBackup)
print("ami created in last 24hours:", amiCount)
print("missing backup:", amiMissingCount)

##### Generating excel
workbook = xlsxwriter.Workbook('backupReport.xlsx')
worksheet = workbook.add_worksheet()
backupReport = (
    ['AwsAccountId', accountId],
    ['InstanceAvailabel', availableInstanceCount],
    ['InstanceForBackup', availableInstanceCountForBackup],
    ['AmiCreated', amiCount],
    ['InstanceMissingBackup', amiMissingCount]
)
row = 0
col = 0

for property, count in (backupReport):
    worksheet.write(row, col, property)
    worksheet.write(row + 1, col , count)
    col +=1
workbook.close()

######## Mailing
#Setup the MIME
message = MIMEMultipart()
message['From'] = sender_email
message['To'] = receiver_email
message['Subject'] = 'Backup Report'
#The subject line
#The body and the attachments for the mail
message.attach(MIMEText(mail_content, 'plain'))
attach_file_name = 'backupReport.xlsx'
attach_file = open(attach_file_name, 'rb') # Open the file as binary mode
content_type = mimetypes.guess_type(attach_file_name)[0].split("/")
payload = MIMEBase(content_type[0], content_type[1])
payload.set_payload((attach_file).read())
encoders.encode_base64(payload) #encode the attachment
#add payload header with filename
payload.add_header('Content-Disposition', 'attachment', filename=attach_file_name)
message.attach(payload)
#Create SMTP session for sending the mail
session = smtplib.SMTP('smtp.gmail.com', port) #use gmail with port
session.starttls() #enable security
session.login(sender_email, password) #login with mail_id and password
text = message.as_string()
session.sendmail(sender_email, receiver_email, text)
session.quit()
print('Mail Sent')

