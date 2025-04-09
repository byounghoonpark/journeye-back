#!/bin/bash
exec daphne -b 0.0.0.0 -p 8000 hotel_admin.asgi:application
