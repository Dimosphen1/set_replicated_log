#! /usr/bin/bash

printf '\n------ STARTING THE CONFIGURATION -----\n'
docker-compose up -d --build
sleep 5


printf '\n\n\n------ MAKE A GET REQUEST TO MASTER -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080'

printf '\n\n\n----- MAKE A GET REQUEST TO SECONDARY -----\n'
curl --request GET -sL \
     --url 'http://localhost:8081'


printf '\n\n\n------ MAKE A POST REQUEST TO MASTER -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Some important data"}'

printf '\n\n\n------ MAKE A GET REQUEST TO MASTER -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080'

printf '\n\n\n----- MAKE A GET REQUEST TO SECONDARY -----\n'
curl --request GET -sL \
     --url 'http://localhost:8081'

printf '\n\n\n------ MAKE A POST REQUEST TO SECONDARY -----\n'
curl --request POST -sL \
     --url 'http://localhost:8081'\
     --data '{"message": "Some undesired data"}'

printf '\n\n\n------ STOP THE CONFIGURATION -----\n'
docker-compose down
