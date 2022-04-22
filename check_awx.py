#!/usr/bin/env python3

import argparse
import json
import sys

from requests import get
from datetime import datetime
from datetime import timedelta


# Global variables
VERSION = '0.1.0'
WEBSITE = 'https://github.com/CrononDE/check_awx'

OK       = 0
WARNING  = 1
CRITICAL = 2
UNKNOWN  = 3

instances_critical =[]
instances_warning =[]
instances_healthy = []


# Class for using multiple formater
class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.MetavarTypeHelpFormatter):
    pass

# Parser for user input
parser = argparse.ArgumentParser(description='Check AWX instances')
parser_global = parser.add_argument_group('global')
parser_global.add_argument('--host', type=str, required=True, help='Hostname of AWX instance (must include http(s) protocol)')

# token xor token_file is required
group_token = parser_global.add_mutually_exclusive_group(required=True)
group_token.add_argument('--token', type=str, help='API Token of AWX instance')
group_token.add_argument('--token_file', dest='file', type=argparse.FileType('r'), help='File to API Token of AWX instance')

# Subparsers
subparsers = parser.add_subparsers(title='checks', dest='command')

p_events_mem = subparsers.add_parser('events_in_mem', help='Check the number of events in redis memory', formatter_class=CustomFormatter)
p_events_mem.add_argument('--warn', type=int, default=50, help='Warning threshold')
p_events_mem.add_argument('--crit', type=int, default=100, help='Critical threshold')

p_events_queue = subparsers.add_parser('events_in_queue', help='Check the number of events in redis queue', formatter_class=CustomFormatter)
p_events_queue.add_argument('--warn', type=int, default=50, help='Warning threshold')
p_events_queue.add_argument('--crit', type=int, default=100, help='Critical threshold')

p_int_capacity = subparsers.add_parser('int_capacity', help='Check remaning capacity of all instances ', formatter_class=CustomFormatter)
p_int_capacity.add_argument('--warn', type=int, default=25, help='Warning threshold')
p_int_capacity.add_argument('--crit', type=int, default=10, help='Critical threshold')

p_int_health = subparsers.add_parser('int_health', help='Check last health check of all instances ', formatter_class=CustomFormatter)
p_int_health.add_argument('--warn', type=int, default=120, help='Warning threshold')
p_int_health.add_argument('--crit', type=int, default=300, help='Critical threshold')

p_pending_jobs = subparsers.add_parser('pending_jobs', help='Check the number of pending jobs', formatter_class=CustomFormatter)
p_pending_jobs.add_argument('--warn', type=int, default=10, help='Warning threshold')
p_pending_jobs.add_argument('--crit', type=int, default=20, help='Critical threshold')

args = parser.parse_args()


# Functions

# Get API response
# FIXME: Check protocol was defined
# FIXME: Check response was valid
def api_response(api_path):

    if args.token:
        token = args.token

    if args.file:
        token = args.file.read().strip('\n')

    endpoint = args.host + api_path
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    return get(endpoint, headers=headers).json()

# Checks
def events_in_mem():
    api_response_full = api_response('/api/v2/metrics/')
    events_in_mem_instances = api_response_full['callback_receiver_events_in_memory']['samples']
    healthy_instances = []

    for instance in events_in_mem_instances:
        instance_name = instance['labels']['node']
        instance_value = instance['value']

        if instance_value >= args.crit:
            instances_critical.append({'name': instance_name, 'value': instance_value})
        elif instance_value >= args.warn:
            instances_warning.append({'name': instance_name, 'value': instance_value})
        else:
            instances_healthy.append({'name': instance_name, 'value': instance_value})

def events_in_queue():
    api_response_full = api_response('/api/v2/metrics/')
    events_in_queue_instances = api_response_full['callback_receiver_events_queue_size_redis']['samples']
    healthy_instances = []

    for instance in events_in_queue_instances:
        instance_name = instance['labels']['node']
        instance_value = instance['value']

        if instance_value >= args.crit:
            instances_critical.append({'name': instance_name, 'value': instance_value})
        elif instance_value >= args.warn:
            instances_warning.append({'name': instance_name, 'value': instance_value})
        else:
            instances_healthy.append({'name': instance_name, 'value': instance_value})

def int_capacity():
    api_response_full = api_response('/api/v2/instances/')
    int_capacity_instances = api_response_full['results']
    healthy_instances = []

    for instance in int_capacity_instances:
        if instance['capacity'] > 0:
            if instance['percent_capacity_remaining'] <= args.crit:
                instances_critical.append({'name': instance['hostname'], 'value': instance['percent_capacity_remaining']})
            elif instance['percent_capacity_remaining'] <= args.warn:
                instances_warning.append({'name': instance['hostname'], 'value': instance['percent_capacity_remaining']})
            else:
                instances_healthy.append({'name': instance['hostname'], 'value': instance['percent_capacity_remaining']})

def int_health():
    api_response_full = api_response('/api/v2/instances/')
    int_health_instances = api_response_full['results']

    current_time_utc = datetime.utcnow()
    datetime_awx_pattern = '%Y-%m-%dT%H:%M:%S.%fZ'

    for instance in int_health_instances:
        last_health_check = datetime.strptime(instance['last_health_check'], datetime_awx_pattern)

        if (last_health_check + timedelta(seconds=args.crit)) <= current_time_utc:
            instances_critical.append({'name': instance['hostname'], 'value': instance['last_health_check']})
        elif (last_health_check + timedelta(seconds=args.warn)) <= current_time_utc:
            instances_warning.append({'name': instance['hostname'], 'value': instance['last_health_check']})
        else:
            instances_healthy.append({'name': instance['hostname'], 'value': instance['last_health_check']})

def pending_jobs():
    api_response_full = api_response('/api/v2/metrics/')
    pending_jobs = api_response_full['awx_pending_jobs_total']['samples'][0]['value']

    if pending_jobs >= args.crit:
        instances_critical.append({'name': 'AWX', 'value': pending_jobs})
    elif pending_jobs >= args.warn:
        instances_warning.append({'name': 'AWX', 'value': pending_jobs})
    else:
        instances_healthy.append({'name': 'AWX', 'value': pending_jobs})

def report():
    for instance in instances_critical:
        print("CRITICAL: " + instance['name'] + ' (' + str(instance['value']) + ')', file=sys.stderr)

    for instance in instances_warning:
        print("WARNING: " + instance['name'] + ' (' + str(instance['value']) + ')', file=sys.stderr)

    for instance in instances_healthy:
        print("OK: " + instance['name'] + ' (' + str(instance['value']) + ')')

    if instances_critical:
        sys.exit(CRITICAL)

    if instances_warning:
        sys.exit(WARNING)

action_fuctions = {'events_in_mem': events_in_mem,
                   'events_in_queue': events_in_queue,
                   'int_capacity': int_capacity,
                   'int_health': int_health,
                   'pending_jobs': pending_jobs,
                   }

action_fuctions[args.command]()

report()
