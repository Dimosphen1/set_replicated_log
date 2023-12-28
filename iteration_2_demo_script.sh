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
     --data '{"message": "Some important data 1"}'

printf '\n\n\n------ MAKE A GET REQUEST TO MASTER -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080'

printf '\n\n\n----- MAKE A GET REQUEST TO FIRST SECONDARY -----\n'
curl --request GET -sL \
     --url 'http://localhost:8081'

printf '\n\n\n----- MAKE A GET REQUEST TO SECOND SECONDARY -----\n'
curl --request GET -sL \
     --url 'http://localhost:8082'

printf '\n\n\n----- MAKE A DELAYED GET REQUEST TO SECOND SECONDARY -----\n'
sleep 7
curl --request GET -sL \
     --url 'http://localhost:8082'

printf '\n\n\n------ MAKE A POST REQUEST TO MASTER TO CHECK ORDER -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Some important data 2"}'

printf '\n\n\n------ CHECK MESSAGE ORDER IN MASTER -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080'

printf '\n\n\n------ CHECK MESSAGE ORDER IN FIRST SECONDARY -----\n'
curl --request GET -sL \
     --url 'http://localhost:8081'

printf '\n\n\n------ STOP THE CONFIGURATION -----\n'
docker-compose down
