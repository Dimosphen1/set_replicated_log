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