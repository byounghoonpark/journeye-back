#!/bin/bash
exec celery -A hotel_admin worker --loglevel=info
