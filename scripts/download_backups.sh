#!/bin/bash

mkdir -p backups
D=`date +'%F_%H-%M'`
if [ -d "backups/$D" ]; then
  rm -fr "backups/$D"
fi 
mkdir "backups/$D"
# "backups/$D"
pwd

echo '
rm -fr /tmp/dump
mongodump -d gkc -o /tmp/dump
' | ssh -i /Users/peterbe/dev/AWS/kwissle.pem ubuntu@ec2-50-17-186-217.compute-1.amazonaws.com
rsync 


rsync -avzP -e "ssh -i /Users/peterbe/dev/AWS/kwissle.pem" ubuntu@ec2-50-17-186-217.compute-1.amazonaws.com:/tmp/dump "backups/$D"
