#!/bin/bash
docker-compose down -v; docker-compose --profile pytests up --build --abort-on-container-exit
