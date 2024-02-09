#! /usr/bin/bash

printf '\n------ STARTING THE CONFIGURATION -----\n'
docker-compose up -d --build
sleep 5


# SELF-CHECK ACCEPTANCE TEST
printf '\n\n\n----- PAUSE SECOND SECONDARY -----\n'
docker container pause secondary-2

printf '\n\n\n----- CHECK CONTAINERS  -----\n'
docker ps -a

printf '\n\n\n------ MAKE A POST REQUEST TO MASTER WITH FIRST MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg1", "write_concern": 1}'

printf '\n\n\n------ MAKE A POST REQUEST TO MASTER WITH SECOND MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg2", "write_concern": 2}'

printf '\n\n\n------ MAKE A POST REQUEST TO MASTER WITH THIRD MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg3", "write_concern": 3}' &

printf '\n\n\n------ MAKE A POST REQUEST TO MASTER WITH FOURTH MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg4", "write_concern": 1}'

printf '\n\n\n----- UNPAUSE SECOND SECONDARY -----\n'
docker container unpause secondary-2

printf '\n\n\n----- CHECK CONTAINERS  -----\n'
docker ps -a

printf '\n\n\n----- WAIT 5 SECONDS FOR MESSAGES SYNC -----\n'
sleep 5

printf '\n\n\n------ CHECK MESSAGES SECOND SECONDARY -----\n'
curl --request GET -sL \
     --url 'http://localhost:8082'

# HEARTBEATS TEST
printf '\n\n\n----- CHECK SECONDARIES HEALTH  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080/health'

printf '\n\n\n----- CHECK MESSAGES ON MASTER  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080'

printf '\n\n\n----- CHECK MESSAGES ON FIRST SECONDARY  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8081'

printf '\n\n\n----- CHECK MESSAGES ON SECOND SECONDARY  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8082'

printf '\n\n\n----- PAUSE SECOND SECONDARY -----\n'
docker container pause secondary-2

printf '\n\n\n----- WAIT 5 SECONDS FOR HEALTH SYNC -----\n'
sleep 5

printf '\n\n\n----- CHECK SECONDARIES HEALTH  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080/health'

printf '\n\n\n----- WAIT 7 SECONDS FOR HEALTH SYNC -----\n'
sleep 7

printf '\n\n\n----- CHECK SECONDARIES HEALTH  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080/health'

printf '\n\n\n------ MAKE A POST REQUEST TO MASTER WITH FIFTH MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg5", "write_concern": 2}'

printf '\n\n\n----- UNPAUSE SECOND SECONDARY -----\n'
docker container unpause secondary-2

printf '\n\n\n----- WAIT 5 SECONDS FOR MESSAGES SYNC -----\n'
sleep 5

printf '\n\n\n----- CHECK SECONDARIES HEALTH  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080/health'

printf '\n\n\n----- CHECK MESSAGES ON SECOND SECONDARY  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8082'

# QUORUM TEST
printf '\n\n\n----- CHECK SECONDARIES HEALTH  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080/health'

printf '\n\n\n----- PAUSE FIRST AND SECOND SECONDARY -----\n'
docker container pause secondary-1 secondary-2

printf '\n\n\n----- WAIT 5 SECONDS FOR HEALTH SYNC -----\n'
sleep 5

printf '\n\n\n----- CHECK SECONDARIES HEALTH  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080/health'

printf '\n\n\n------ TRY TO MAKE A POST REQUEST TO MASTER WITH SIXTH MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg6", "write_concern": 1}'

printf '\n\n\n------ TRY TO MAKE A GET REQUEST TO MASTER -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080'

printf '\n\n\n----- WAIT 7 SECONDS FOR HEALTH SYNC -----\n'
sleep 7

printf '\n\n\n----- CHECK SECONDARIES HEALTH  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080/health'

printf '\n\n\n------ TRY TO MAKE A POST REQUEST TO MASTER WITH SIXTH MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg6", "write_concern": 1}'

printf '\n\n\n------ TRY TO MAKE A GET REQUEST TO MASTER -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080'

printf '\n\n\n----- UNPAUSE FIRST SECONDARY -----\n'
docker container unpause secondary-1

printf '\n\n\n----- WAIT 5 SECONDS FOR HEALTH SYNC -----\n'
sleep 5

printf '\n\n\n------ MAKE A POST REQUEST TO MASTER WITH SIXTH MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg6", "write_concern": 1}'

printf '\n\n\n------ MAKE A POST REQUEST TO MASTER WITH SEVENTH MESSAGE -----\n'
curl --request POST -sL \
     --url 'http://localhost:8080'\
     --data '{"message": "Msg7", "write_concern": 2}'

printf '\n\n\n----- UNPAUSE SECOND SECONDARY -----\n'
docker container unpause secondary-2

printf '\n\n\n----- WAIT 7 SECONDS FOR HEALTH SYNC -----\n'
sleep 7

printf '\n\n\n----- CHECK SECONDARIES HEALTH  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080/health'

printf '\n\n\n----- CHECK MESSAGES ON MASTER  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8080'

printf '\n\n\n----- CHECK MESSAGES ON FIRST SECONDARY  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8081'

printf '\n\n\n----- CHECK MESSAGES ON SECOND SECONDARY  -----\n'
curl --request GET -sL \
     --url 'http://localhost:8082'

printf '\n\n\n------ STOP THE CONFIGURATION -----\n'
docker-compose down
