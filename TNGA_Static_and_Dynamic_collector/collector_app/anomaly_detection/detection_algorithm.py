#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

Anomaly Detection Algorithms
================================

Module that contains the algorithms to detect anomaly

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - to perform logging operations

    Related 3rd Party Library
    =============================

    External Libraries
    * scipy - to perform scientific operations

This script contains the following function

    * main - main function to call appropriate functions to carry out required task

"""

# Standard library imports
import logging

# Related third party imports
from scipy.stats import kruskal

# Local application/library specific imports


__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def kruskal_test(reference_sample, test_sample, alpha=0.05):
    """

    Function that does "Kruskal–Wallis one-way analysis of variance" hypothesis test to see if both the reference
    sample and test sample are from the same same distribution (population)

    :param reference_sample: The reference sample which denotes the set of data for good cycle (of a specific parameter)
    :type reference_sample: list

    :param test_sample: The test sample which needs to be checked for the hypothesis
    :type test_sample: list

    :param alpha: The  p-value (typically ≤ 0.05) to indicate evidence against the null hypothesis (both are from
    same distribution)
    :type alpha: float

    :return: Return whether both samples are from same distribution (1 - OK)  or from different
    distribution (3 - Critical)
    :rtype: int

    """

    # Kruskal-Wallis H-test
    stat, p_value = kruskal(reference_sample, test_sample)

    if p_value > alpha:
        LOGGER.debug('Same distributions (fail to reject H0)')
        return 1
    else:
        LOGGER.debug('Different distributions (reject H0)')
        return 3


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to carry out required task

    """


if __name__ == '__main__':
    main()
