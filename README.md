## Replicated log

### Iteration 1

The project contains two folders: 
- `master` - to store the code for master server and a corresponding Dockerfile;
- `secondary` - to store the code for secondary server and a corresponding Dockerfile;

Besides folders, there is a bash script `interation_1_demo_script.sh` <br> 
that initializes the configuration, makes GET and POST requests to the <br>
<b>Master</b> and <b>Secondary</b> servers and after that deletes the configuration:
```shell
bash iteration_1_demo_script.sh
```

The `POST` request is slowed down due to the delay in the writing operation on one <br>
of the <b>Secondary</b> servers to mimic the delay. The <b>Master</b> server waits for acknowledgement <br>
from both <b>Secondary</b> servers, only after that write happens.

In the current version, the mechanisms of retries are not implemented, because of <br>
that the write fails in case at least one <b>Secondary</b> server does not acknowledge write.

For communication between nodes the port `80` is that that is not exposed from the outer <br>
network. <b>Master</b> server support `GET` and `POST` requests on port `8080` that is exposed <br>
to the external access, and <b>Secondary</b> servers support only `GET` requests on <br> 
ports `8081` and `8082` correspondingly.

### Iteration 2

The aim of this iteration is to provide a semi-synchronous replication of messages from master  <br>
to secondaries with an eventual consistency. To achieve that, a new environmental variable  <br>
`WRITE_CONCERN` is introduced. There are several options that it could take:
- `WRITE_CONCERN=1` (client receives response when write happens to the Master <br>
without acknowledgment from replicas);
- `WRITE_CONCERN=2` (client receives response when write happens to the Master <br>
with an acknowledgment from one replica);
- `WRITE_CONCERN=3` (client receives response when write happens to the Master <br>
with an acknowledgment from two replicas).

The inconsistency is emulated via a delay in writing to the secondary replica `secondary-2 ` <br>
that sleeps for 5 seconds during the write processing.

Besides that, there are two new methods introduced to the <b>Secondary</b> servers:
- `deduplicate_messages`;
- `order_messages`.

They are used to provide message deduplication and ordering during the writing operation. <br>

To emulate this behaviour there is an `iteration_2_demo_script.sh` that creates a setup, <br>
performs requests to different servers and after that deletes the configuration:
```shell
bash iteration_2_demo_script.sh
```

### Iteration 3

This iteration introduces the features of retries, heartbeats (health checks), and quorum <br>
append. Besides that, the deduplication and ordering functionality is improved as well.

#### New environmental variables
- `QUORUM` - defines the least number of secondaries in the healthy state required to <br>
accept the message and perform replication. If not reached, the master becomes available in <br>
a read mode only;
- `REPLICATE_TIMEOUT` - the timeout that is set for message replication request <br>
before failing with the timeout exception;
- `MAX_RETRIES` - the number of retries allowed before considering that the message <br>
replication failed;
- `HEALTHCHECK_INTERVAL` - the interval of performing heartbeats by master to check <br>
the secondaries' health;  
- `HEALTHCHECK_REQUEST_TIMEOUT` - the timeout that is set for heartbeat request <br>
before failing with the timeout exception;
- `HEALTHCHECK_SUSPECT_THRESHOLD` - the threshold that defines the number of <br>
consecutive failed health checks before considering the secondary unhealthy.

#### Replication mechanism
The replication is performed using the exponential backoff and depends on the <br>
status of the secondary. In case the secondary is considered unhealthy, the <br>
retries are stopped. When secondary changes state from unhealthy to healthy, <br>
the master replicates missed messages to the secondary thus keeping the <br>
consistency of the installation.

#### Heartbeats
The heartbeats coroutines have the highest priority among others and allow <br>
adjusting the behavior of retries depending on the state of the secondaries. <br>
In case during the heartbeat the secondary is detected as unhealthy, all existing <br>
retry coroutines stop execution. The replication of the missed messages continues <br>
upon the rejoining of the secondary utilizing the same replication mechanism as <br>
the one involved in the initial message replication.

#### Quorum append
The number of secondaries required to perform the replication is defined by the <br>
`QUORUM` variable. It is mandatory for the defined number of secondaries to be in <br>
the healthy status. In case the number is not reached, the master shifts to the <br>
read-only mode and does not serve to append new messages.

#### Improved deduplication
In this iteration, the message deduplication on secondaries includes serialization <br>
of the incoming messages to a hashable state, after that exclusion of duplicates <br>
and leaving only messages with a unique hash retrieved from the incoming message <br>
text, order, and timestamp.

#### Improved ordering
Since several messages could be delayed and there is a requirement of not retrieving <br>
the messages obtained earlier that corrupt order, there is an additional property of  <br>
messages named `order` that allow to return to the clients only messages with <br>
consecutive order. In case some messages are obtained earlier than the preceding ones, <br>
they would not be displayed to the clients before having the consecutive message order <br>
preserved.

To emulate and test the behavior discussed there is an `iteration_3_demo_script.sh` <br>
that creates a setup, performs requests to different servers, and after that deletes the <br>
configuration:
```shell
bash iteration_3_demo_script.sh
``` 
The example output of the script is added in the `iteration_3_demo_script_execution.txt` <br>
file.
