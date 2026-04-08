# asimpy version 0.17.0

| Feature                           | Executions | Instructions | Instr/Execution |
| :---------------------------------|----------: |------------: |---------------: |
| AllOf                             |       1000 |       338199 |           338.2 |
| AllOf (blocking)                  |       1000 |       674354 |           674.4 |
| Barrier                           |       1000 |       440368 |           440.4 |
| Container                         |       1000 |       273233 |           273.2 |
| Container (float amounts)         |       1000 |       273233 |           273.2 |
| Container (non-blocking)          |       1000 |        53233 |            53.2 |
| Environment.get_log               |       1000 |        11199 |            11.2 |
| Environment.log                   |       1000 |        20199 |            20.2 |
| Environment.run(until=)           |       1000 |       253291 |           253.3 |
| Event                             |       1000 |       181199 |           181.2 |
| Event (cancel)                    |       1000 |        42199 |            42.2 |
| Event (fail)                      |       1000 |       210202 |           210.2 |
| FirstOf                           |       1000 |       326199 |           326.2 |
| FirstOf (blocking)                |       1000 |       659354 |           659.4 |
| Interrupt                         |       1000 |       532357 |           532.4 |
| Interrupt (with cause)            |       1000 |       540357 |           540.4 |
| PreemptiveResource                |       1000 |       922381 |           922.4 |
| PreemptiveResource (cause fields) |       1000 |       933381 |           933.4 |
| PreemptiveResource (no-preempt)   |       1000 |       829272 |           829.3 |
| PriorityQueue                     |       1000 |       271243 |           271.2 |
| Process                           |       1000 |       349096 |           349.1 |
| Queue                             |       1000 |       268232 |           268.2 |
| Queue (blocking get)              |       1000 |       553381 |           553.4 |
| Queue (blocking put)              |       1000 |       606301 |           606.3 |
| Queue (non-blocking)              |       1000 |        53226 |            53.2 |
| Resource (contention)             |       1000 |       565040 |           565.0 |
| Resource (context manager)        |       1000 |       160223 |           160.2 |
| Resource (multi-capacity)         |       1000 |       563311 |           563.3 |
| Resource (try_acquire)            |       1000 |        39223 |            39.2 |
| Resource (uncontended)            |       1000 |       138223 |           138.2 |
| Store                             |       1000 |       264227 |           264.2 |
| Store (filtered get)              |       1000 |       273230 |           273.2 |
| Store (non-blocking)              |       1000 |        47225 |            47.2 |
| Timeout                           |       1000 |       252199 |           252.2 |
