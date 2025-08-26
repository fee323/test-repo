


Feature: Production Order FSTUser

@critical
Scenario: Visit Production order page and click on Edit btn
    Given we visit "orders/SalesOrderFSTUser"
    when we edit the top row
