#!/bin/bash
docker-compose down -v; docker-compose --profile $1 up --build
