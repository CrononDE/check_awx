```sh
usage: check_awx.py [-h] --host HOST (--token TOKEN | --token_file FILE)
                    {events_in_mem,events_in_queue,int_capacity,int_health,pending_jobs}
                    ...

Check AWX instances

optional arguments:
  -h, --help            show this help message and exit

global:
  --host HOST           Hostname of AWX instance
  --token TOKEN         API Token of AWX instance
  --token_file FILE     File to API Token of AWX instance

checks:
  {events_in_mem,events_in_queue,int_capacity,int_health,pending_jobs}
    events_in_mem       Check the number of events in redis memory
    events_in_queue     Check the number of events in redis queue
    int_capacity        Check remaning capacity of all instances
    int_health          Check last health check of all instances
    pending_jobs        Check the number of pending jobs
```
