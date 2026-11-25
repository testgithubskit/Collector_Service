#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Response Model Classes
================================

Module that contains pydantic classes for the api endpoint response models in the application

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - To perform logging operations.

    Related 3rd Party Library
    =============================

    * pydantic - To perform data validation and settings management using python type annotations.
"""

# Standard library imports
from typing import Optional

# Related third party imports
from pydantic import BaseModel

# Local application/library specific imports
# None

__author__ = "smt18m005@iiitdm.ac.in"


class RequestUserModel(BaseModel):
    """
    PYDANTIC MODEL FOR USER IN DATABASE
    ==========================================

    This is a class (pydantic class) to represent a user, for authentication purposes.
    """

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
