


Feature: Sales invoice MT

@critical
Scenario: Visit Sales invoice page
    Given we visit "orders/salesInvoice_MT"
#    when we edit the top row
    when we clear the from date and search
