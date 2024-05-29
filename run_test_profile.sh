#!/bin/bash
TEST_PKG=$2 docker-compose down -v; docker-compose --profile $1 up --build
