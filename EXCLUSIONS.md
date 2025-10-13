# Performance Management Distribution Calculation

This file attempts to describe how the calculation of distribution percentages by performance level works as there are a few excluions and roll-ups that occurr based on corporate policy.  

## Goal

- The goals of these directives is to guide implenentation and give Claude the understanding it needs to build in the logic needed to have the calculations be correct.  This is important because there should be NO hard coded values, percentages, roll-ups, etc based on specifc text of levels.  One must understand these rule and determine a way to simply implement this without the need to hard code values.
- The examples below are just that -- examples.  We should design a system that is configurable and sustainable, and allows the models to be used to facilitate this logic without hardcoding logic based on descriptions or IDs.

## General rules and descriptions

- The top level manager (The associate with nomanager configured (there should only be one)) is not counted in the distribution or in the total number of associates in the performance management pool.  This is because this is the manager who is operating this application.
- There are Performance levels which are not to be considersed in the overall distribution.  An example of this is "Too New".  If an associate is rated in a level that is excluded from distribution, this associate is decucted from the total number of assocites when calculating percentage distributions.  This is one example of a performance level that is excluded.  There may be more.  These should show in reports, but not calculated.
- There is a minimum and maximum distribution percentage for each performance level.  This sets the minumum and maximum aggregate percentage that is allowed for each level to ensure that we are meeting corporate distribution.  WE aim to stay between these teo numbers.
- Distributions for performance levels are a bit more complicated than just straight percentages as sometimes multuple performance levels are counted in the distribution.  For example, Very Strong and Exceptional together are managed to a minumum and maximum distribution, but the percentage of Very Strong to Exceptional is immaterial as long as together we are not over or under the minumum and maximum percentages.
