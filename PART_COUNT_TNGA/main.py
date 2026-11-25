#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Main Module for the Monitoring Application
===============================================

Module for starting point of the FastApi application

This script requires the following modules be installed in the python environment
    * logging - To perform logging operations.
    * fastapi - To perform web application (backend) related functions.
"""

# Standard library imports
import logging

# Related third party imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local application/library specific imports
from machine_monitoring_app.utils.configuration_helper import initialize_server
from machine_monitoring_app.routers import core_data_route, security_routes
#from machine_monitoring_app.database.db_utils import connect_to_mongo, close_mongo_connection


__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)

APP = FastAPI()

ALLOWED_ORIGINS = ["*"]
#ALLOWED_ORIGINS = ["http://localhost:8080", "http://172.18.20.27:8080", "http://172.18.20.27"]

APP.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

APP.add_event_handler("startup", initialize_server)
#APP.add_event_handler("shutdown", close_mongo_connection)

APP.include_router(core_data_route.ROUTER)
APP.include_router(security_routes.ROUTER)

LOGGER.info("Starting Application")

# uvicorn main:APP --reload --host 172.18.7.27 --port 9999
