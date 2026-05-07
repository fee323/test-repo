from behave import given, when, then
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait #shafee
from selenium.webdriver.support import expected_conditions as EC #shafee
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException  #added by shafee
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException#
from selenium.webdriver.support.ui import Select
import time
import json
from assertpy import assert_that




def get_filter(context, filter):
    if filter in context.grid_filters:
        td = context.driver.find_element(By.CSS_SELECTOR, '[id$="-grid"] tr.filters td:nth-child(' + str(context.grid_filters[filter]) + ')')
        inp = td.find_elements(By.TAG_NAME, 'input')
        if not inp:
            return '[id$="-grid"] tr.filters td:nth-child(' + str(context.grid_filters[filter]) + ') select'
        return '[id$="-grid"] tr.filters td:nth-child(' + str(context.grid_filters[filter]) + ') input'
    
    th = context.driver.find_elements(By.CSS_SELECTOR, '[id$="-grid"] tr.filters td')

    i = 0

    for i in range(0, len(th)):
        filter_name = th[i].find_elements(By.TAG_NAME, 'input')
        if not filter_name:
            filter_name = th[i].find_elements(By.TAG_NAME, 'select')
            el = None

            if not filter_name:
                continue
            el = filter_name
            filter_name = filter_name[0].get_attribute('name')
        else:
            el = filter_name
            filter_name = filter_name[0].get_attribute('name')

#        if (filter_name == 'orders_model[' + filter + ']' and el[0].is_displayed()):
        if (filter_name == context.form_prefix[:-1] + '[' + filter + ']' and el[0].is_displayed()): # shafee
            break
    
    context.grid_filters[filter] = i + 1
    return get_filter(context, filter)

def get_vno_filter(context):
    vno = get_filter(context, 'documentTextId')
    return context.driver.find_element(By.CSS_SELECTOR, vno)

def get_vno(context):
    get_vno_filter(context)
    return context.driver.find_element(By.CSS_SELECTOR, '[id$="-grid"] tbody tr:nth-child(1) td:nth-child(' + str(context.grid_filters['documentTextId']) + ') ').text


@when("we store the top row's DOC Id")
def store_top_vno(context):
    vno = get_vno(context)

    context.vno = vno.strip()

@when('we delete the top row')
def delete_top_row(context):
    actions = ActionChains(context.driver)
    delete_button = context.driver.find_element(By.CSS_SELECTOR, '[id$="-grid"] tbody tr:nth-child(1) a.delete img')
    context.driver.execute_script("window.scrollBy(0, 200);")
    actions.move_to_element(delete_button).click().perform()
    try:
        Alert(context.driver).accept()
    except NoAlertPresentException:
        pass

@when('we edit the row with "{text}"')
def edit_row_by_text(context, text):
    actions = ActionChains(context.driver)

    # Ensure grid has at least one row
    rows = context.driver.find_elements(By.CSS_SELECTOR, '[id$="-grid"] tbody tr')
    assert rows, 'Grid is empty — no rows to edit.'

    target_row = None

    for row in rows:
        if text in row.text:
            target_row = row
            break

    assert target_row, f'Row containing "{text}" not found.'

    # Find edit button inside the row
    edit_btn = target_row.find_element(By.CSS_SELECTOR, 'a.update img')

    # Scroll into view and click
    context.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", edit_btn)
    time.sleep(0.5)

    actions.move_to_element(edit_btn).click().perform()



@when('we clear date field "{field_id}", click submit and edit the row with "{text}"')
def clear_date_submit_and_edit(context, field_id, text):
    actions = ActionChains(context.driver)

    # Step 1: Clear the date field
    date_field = WebDriverWait(context.driver, 10).until(
        EC.presence_of_element_located((By.ID, field_id))
    )
    date_field.clear()
    print(f"Cleared date field with ID: {field_id}")

    # Step 2: Click submit button
    submit_button = WebDriverWait(context.driver, 10).until(
        EC.element_to_be_clickable((By.ID, "date_check"))
    )
    submit_button.click()
    print("Clicked submit button")

    # Step 3: Wait for grid row with text to appear
    try:
        WebDriverWait(context.driver, 10).until(
            lambda driver: any(
                text.strip() in row.text.strip()
                for row in driver.find_elements(By.CSS_SELECTOR, '[id$="-grid"] tbody tr')
            )
        )
    except TimeoutException:
        raise AssertionError(f'Timed out waiting for a row containing "{text}" in grid.')

    # Find and edit the target row
    rows = context.driver.find_elements(By.CSS_SELECTOR, '[id$="-grid"] tbody tr')
    target_row = None

    for row in rows:
        print(f"Row text: {row.text}")
        if text.strip() in row.text.strip():
            target_row = row
            break

    assert target_row, f'Row containing "{text}" not found.'
    edit_btn = target_row.find_element(By.CSS_SELECTOR, 'a.update img')
    context.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", edit_btn)
    time.sleep(0.5)
    actions.move_to_element(edit_btn).click().perform()
    print(f"Clicked edit on row containing '{text}'")




@when('we edit the top row')  # or your actual step
def step_impl(context):
    try:
        #  Wait for edit buttons to load
        WebDriverWait(context.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'img[src*="update.png"]'))
        )

        #  Find the first edit button
        edit_button = context.driver.find_elements(By.CSS_SELECTOR, 'img[src*="update.png"]')[0]

        #  Scroll to edit button to make sure it's in view
        context.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edit_button)
        time.sleep(3)

        #  Click the edit button
        edit_button.click()
        time.sleep(3)

    except (IndexError, NoSuchElementException):
        assert False, " Edit button not found in the grid"
    except (TimeoutException, ElementClickInterceptedException, StaleElementReferenceException):
        assert False, " Edit button could not be clicked or did not open the form"

#@when('we edit the top row')
#def edit_top_row(context):
#    wait = WebDriverWait(context.driver, 10)  #shafee
#    actions = ActionChains(context.driver)
#    #edit_btn = context.driver.find_element(By.CSS_SELECTOR, '#orders-grid tbody tr:nth-child(1) a.update img')
#    edit_btn = context.driver.find_element(By.CSS_SELECTOR, '[id$="-grid"] tbody tr:nth-child(1) a.update img')
#    context.driver.execute_script("window.scrollBy(0, 200);")
#    actions.move_to_element(edit_btn).click().perform()
#    time.sleep(8)

@then('we should see this entry in grid')
def find_grid_entry(context):
    if not context.table:
        context.table = context.loaded_table
    values = context.table[0]

    for key in context.table.headings:
        time.sleep(8)
        filter = get_filter(context, key)
        el = context.driver.find_element(By.CSS_SELECTOR, filter)
        ActionChains(context.driver).move_to_element(el).perform()
        context.driver.execute_script("window.scrollBy(0, 200);")

        if el.tag_name == 'select':
            Select(el).select_by_visible_text(values[key])
        else:
            el.send_keys(values[key])
            el.send_keys(Keys.ENTER)
            el.send_keys(Keys.TAB)

    context.driver.implicitly_wait(10)

    try:
        context.driver.find_element(By.CSS_SELECTOR, '[id$="-grid"] .empty')
        context.driver.implicitly_wait(2)
        assert False, 'Element not found in grid'
    except NoSuchElementException:
        pass


#@then('we should see this entry in grid') #added by shafee
#def find_grid_entry(context):
#    if not context.table:
#       context.table = context.loaded_table
#    values = context.table[0]
#
 #   for key in context.table.headings:
  #      for attempt in range(3):
   #         try:
    #            filter_selector = get_filter(context, key)
     #           el = context.driver.find_element(By.CSS_SELECTOR, filter_selector)
      #          ActionChains(context.driver).move_to_element(el).perform()
       #         context.driver.execute_script("window.scrollBy(0, 200);")
#
 #               if el.tag_name == 'select':
  #                  Select(el).select_by_visible_text(values[key])
   #             else:
    #                el.clear()
     #               el.send_keys(values[key])
      #              el.send_keys(Keys.ENTER)
       #             el.send_keys(Keys.TAB)
#
 #               break  # Success
  #          except StaleElementReferenceException:
   #             time.sleep(1)
    #    else:
     #       assert False, f'Element for filter {key} kept going stale'
#
 #   context.driver.implicitly_wait(10)
  #  try:
   #     context.driver.find_element(By.CSS_SELECTOR, '[id$="-grid"] .empty')
    #    context.driver.implicitly_wait(2)
     #   assert False, 'Element not found in grid'
  #  except NoSuchElementException:
   #     pass


@then('we should not see the stored Doc Id')
def delete_top_row(context):
    if context.vno == None:
        assert False, 'No doc Id stored'
    time.sleep(8)
    vno_filter = get_vno_filter(context)
    ActionChains(context.driver).move_to_element(vno_filter).send_keys_to_element(vno_filter, context.vno).send_keys(Keys.ENTER + Keys.TAB).perform()

    context.driver.implicitly_wait(10)

    try:
        context.driver.find_element(By.CSS_SELECTOR, '[id$="-grid"] .empty')

        context.driver.implicitly_wait(2)
    except NoSuchElementException:
        assert False, 'Element not deleted'

def is_float(v):
      try:
        f=float(v)
      except ValueError:
        return False
      return True


@then('we should see "{value}" in "{field}"')
def compare_value(context, value, field):
    field_element = context.driver.find_element(By.ID, context.form_prefix + field)
    field_val = None

    if field_element.tag_name == 'select':
        field_val = Select(field_element).first_selected_option.text
    else:
        field_val = field_element.get_attribute('value')

    def is_floatable(s):
        try:
            float(s.replace(',', '').replace('Rs.', '').strip())
            return True
        except:
            return False

    if is_floatable(field_val) and is_floatable(value):
        assert_that(
            float(field_val.replace(',', '').replace('Rs.', '').strip())
        ).is_equal_to(
            float(value.replace(',', '').replace('Rs.', '').strip())
        )
    else:
        assert_that(field_val.strip()).is_equal_to(value.strip())


#@then('we should see "{value}" in "{field}"')
#def compare_value(context, value, field):
#    # Handle special autocomplete fields with visible value in a separate ID
#    if field == "accountCustomerId":
#        visible_input_id = 'ac_' + context.form_prefix + field + '_ac'
#        field_val = context.driver.find_element(By.ID, visible_input_id).get_attribute('value').strip()
#        assert_that(field_val).is_equal_to(value.strip())
#        return
#
#    # Default path for other fields
#    field_elem = context.driver.find_element(By.ID, context.form_prefix + field)
#    if field_elem.tag_name == 'select':
#        field_val = Select(field_elem).first_selected_option.text
#    else:
#        field_val = field_elem.get_attribute('value')
#        if is_float(field_val):
#            assert_that(float(field_val.replace(',', '').replace('Rs.', '').strip())).is_equal_to(
#                float(value.replace(',', '').replace('Rs.', '').strip())
#            )
#            return
#
#    assert_that(field_val.strip()).is_equal_to(value.strip())


#@then('we should see "{value}" in "{field}"')
#def compare_value(context, value, field):
#    field = context.driver.find_element(By.ID, context.form_prefix + field) # shafee
#    #field = context.driver.find_element(By.ID, 'orders_model_' + field)
#    field_val = None
#    if field.tag_name == 'select':
#        field_val = Select(field).first_selected_option.text
#    else:
#        field_val = field.get_attribute('value')
#    if is_float(field_val):
#        assert_that(float(field_val)).is_equal_to(float(value))
#    else:
#        assert_that(field_val).is_equal_to(value)


@then('we should see "{value}" in "{field}" autocomplete')
def compare_autocomplete_text(context, value, field):
    field = context.driver.find_element(By.ID, 'ac_' + context.form_prefix + field + '_ac')
#    field = context.driver.find_element(By.ID, 'ac_orders_model_' + field + '_ac')
    assert_that(field.get_attribute('value')).is_equal_to(value)



@then('we should see the following in grid')
def fill_grid(context):
    if not context.table:
        context.table = context.loaded_table
    grid_list = [list(row) for row in context.table]

    grid_list = json.dumps(grid_list)

    script = """
    function compareTableWithArray(arrayToCompare) {
        var rowCount = 0;
        var colCount = 1;
        var rows = [];

        $("#ordersProductsTable").find('tr').each(function() {
            rowCount++;

            colCount = 1;
            var data = [];
            // Extract data from 'td' elements
            $(this).find('td').each(function (index, value) {
                if (colCount <= 1) {
                    if ($(this).css('display') != 'none') {
                        var text = $(this).text().trim()
                        data.push(text);
                    }
                }
                colCount++;

                if ($(this).css('display') != 'none') {
                    $(this).find('select').each(function () {
                        if ($(this).css('display') != 'none') {
                            var text = $("#" + this.id + " option:selected").text();
                            data.push(text);
                        }
                    });

                    $(this).find('textarea').each(function () {
                        if ($(this).css('display') != 'none') {
                            var text = $("#" + this.id).val();
                            data.push(text);
                        }
                    });

                    $(this).find('input').each(function () {
                        if ($(this).css('display') != 'none') {
                            var text = $(this).val();
                            data.push(text);
                        }
                    });
                }
            });
            rows.push(data);
        });

        for (var i = 0; i < arrayToCompare.length; i++) {
            for (let j = 0; j < arrayToCompare[0].length; j++) {
                if (rows[i + 1] == null || (rows[i + 1][j + 1] ?? "").trim() != String(arrayToCompare[i][j] ?? "").trim() && Number(rows[i + 1][j + 1]) != Number(arrayToCompare[i][j])) {
                    console.log('Mismatch found at row ' + (i + 1));
                    return false;
                }
            }
        }

        console.log('Table and array match.');
        return true;
    }

    return compareTableWithArray(""" + grid_list + """)
    """
    time.sleep(8)

    result = context.driver.execute_script(script)
    print(result)
    assert_that(result).is_true()


@then('the first {row_count:d} rows in grid should be completely filled')
def check_grid_rows_not_empty(context, row_count):
    # Wait for the grid table to appear before proceeding
    WebDriverWait(context.driver, 10).until(
        EC.presence_of_element_located((By.ID, "ordersProductsTable"))
    )
    print("✅ Grid is now visible.")

    time.sleep(1)  # Optional slight wait if needed

    script = f"""
    function checkGridFilled(rowLimit) {{
        var valid = true;
        var rowIndex = 0;

        var rows = $("#ordersProductsTable tr").filter(function() {{
            return $(this).find("td").length > 0;
        }});

        if (rows.length === 0) {{
            console.log("❌ No rows found in grid.");
            return false;
        }}

        rows.each(function () {{
            if (rowIndex >= rowLimit) return false;

            this.scrollIntoView({{ behavior: 'auto', block: 'center' }});

            var rowHasEmpty = false;

            $(this).find("td").each(function () {{
                if ($(this).css("display") === "none") return;

                let cellText = $(this).text().trim();
                let hasInput = false;
                let finalValue = "";

                $(this).find("input:visible").each(function () {{
                    hasInput = true;
                    finalValue = $(this).val().trim();
                }});

                $(this).find("select:visible").each(function () {{
                    hasInput = true;
                    finalValue = $(this).find("option:selected").text().trim();
                }});

                $(this).find("textarea:visible").each(function () {{
                    hasInput = true;
                    finalValue = $(this).val().trim();
                }});

                if (!hasInput && cellText === "") {{
                    rowHasEmpty = true;
                    console.log("❌ Empty plain cell.");
                    return false;
                }}

                if (hasInput && finalValue === "") {{
                    rowHasEmpty = true;
                    console.log("❌ Empty input/select/textarea.");
                    return false;
                }}
            }});

            if (rowHasEmpty) {{
                console.log("❌ Empty cell found in row " + (rowIndex + 1));
                valid = false;
                return false;
            }}

            rowIndex++;
        }});

        return valid;
    }}

    return checkGridFilled({row_count});
    """

    result = context.driver.execute_script(script)
    print(f"✅ Grid row check result: {result}")
    assert_that(result).is_true()



#@then('the first {row_count:d} rows in grid should be completely filled') #added by faheem bhae
#def check_grid_rows_not_empty(context, row_count):
#    time.sleep(8)
#    script = f"""
#    function checkRowsNotEmpty(rowLimit) {{
#        var rowIndex = 0;
#        var valid = true;
#
#        $("#ordersProductsTable tr").each(function () {{
#            if (rowIndex >= rowLimit) return false;  // Break after N rows
#            if (rowIndex === 0) {{
#                rowIndex++; // skip header
#                return;
#            }}
#
#            var rowHasEmptyCell = false;
#
#            $(this).find('td').each(function () {{
#                if ($(this).css('display') === 'none') return;
#
#                var cellText = $(this).text().trim();
#                var hasInput = false;
#
#                $(this).find('select:visible').each(function () {{
#                    if (!$("#" + this.id + " option:selected").text().trim()) {{
#                        rowHasEmptyCell = true;
#                        return false;
#                    }}
#                    hasInput = true;
#                }});
#
#                $(this).find('textarea:visible').each(function () {{
#                    if (!$("#" + this.id).val().trim()) {{
#                        rowHasEmptyCell = true;
#                        return false;
#                    }}
#                    hasInput = true;
#                }});
#
#                $(this).find('input:visible').each(function () {{
#                    if (!$(this).val().trim()) {{
#                        rowHasEmptyCell = true;
#                        return false;
#                    }}
#                    hasInput = true;
#                }});
#
#                if (!hasInput && cellText === '') {{
#                    rowHasEmptyCell = true;
#                    return false;
#                }}
#            }});
#
#            if (rowHasEmptyCell) {{
#                valid = false;
#                return false; // break loop early
#            }}
#
#            rowIndex++;
#        }});
#
#        return valid;
#    }}
#
#    return checkRowsNotEmpty({row_count});
#    """
#
#    result = context.driver.execute_script(script)
#    print(f"Grid row check result: {result}")
#    assert_that(result).is_true()

@then('row {row_num:d} in grid "{grid_id}" should be completely filled')
def check_specific_grid_row_filled(context, row_num, grid_id):
    script = f"""
    function checkSpecificRowNotEmpty(gridId, rowIndex) {{
        var grid = document.getElementById(gridId);
        if (!grid) return false;

        var rows = grid.querySelectorAll("tbody tr");
        if (rows.length < rowIndex) return false;

        var row = rows[rowIndex - 1];  // 0-based index
        var cells = row.querySelectorAll("td");

        for (var j = 0; j < cells.length; j++) {{
            if (cells[j].style.display === 'none') continue;

            var input = cells[j].querySelector("input, select, textarea");
            if (input && input.offsetParent !== null) {{
                var val = input.value.trim();
                if (!val) {{
                    console.log("Empty input/select/textarea at Row " + rowIndex + ", Col " + (j+1));
                    return false;
                }}
            }} else {{
                var text = cells[j].textContent.trim();
                if (!text) {{
                    console.log("Empty text at Row " + rowIndex + ", Col " + (j+1));
                    return false;
                }}
            }}
        }}
        return true;
    }}
    return checkSpecificRowNotEmpty("{grid_id}", {row_num});
    """

    result = context.driver.execute_script(script)
    print(f"Row {row_num} check result: {result}")
    assert result, f"Grid '{grid_id}' Row {row_num} has empty cells"




