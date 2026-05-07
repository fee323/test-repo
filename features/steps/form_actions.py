from behave import given, when, then
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import json
import time

# Import helper functions from environment
from features.environment import navigate_to_page_with_retry, wait_for_element_with_auto_refresh



#@given('we visit "{url}"')
#def visit_url(context, url):
#    context.driver.get('https://' + context.domain  + '/admin/?r=' + url)

#    if "accounts2" in url.lower():
#           context.form_prefix = "accounts_"
#    else:
#            context.form_prefix = "orders_model_"
#    try:
#        WebDriverWait(context.driver, 8).until(
#            EC.presence_of_element_located((By.ID, 'title'))  # Or any reliable element
#        )
#        print(f"✅ Successfully loaded {url}")
#    except TimeoutException:
#        context.driver.save_screenshot(f"visit_{url}_fail.png")
#        assert False, f"❌ Failed to load page {url}"



@given('we visit "{url}"')#added by shafee
def visit_url(context, url):
    context.driver.get('https://' + context.domain  + '/admin/?r=' + url)

    if "accounts2" in url.lower():
        context.form_prefix = "accounts_"
    else:
        context.form_prefix = "orders_model_"

    # Wait for page to load
#    time.sleep(2)

    # Check for error message
    error_messages = [
        "ERROR 404",
        "The system is unable to find the requested action"
    ]

    page_source = context.driver.page_source

    for error in error_messages:
        if error in page_source:
            context.driver.save_screenshot(f"visit_{url}_404.png")
#            assert False, f" Page at '{url}' returned error: {error}"
            msg = f"Page at '{url}' returned error: {error}"
            print(msg)
            assert False, msg

    print(f" Successfully loaded {url}")



@given('we wait "{seconds}" second')
@when('we wait "{seconds}" seconds')
def delay(context, seconds):
    time.sleep(int(seconds))

@given('we select "{text}" in "{field_id}"')
@when('we select "{text}" in "{field_id}"')
@then('we select "{text}" in "{field_id}"')
def select_dropdown(context, text, field_id):
#    dropdown = Select(context.driver.find_element(By.ID, 'orders_model_' + field_id)) 
    dropdown = Select(context.driver.find_element(By.ID, context.form_prefix + field_id)) # by shafee  
    dropdown.select_by_visible_text(text)
    time.sleep(3)

@when('we clear the from date and search')
def step_impl(context):
    WebDriverWait(context.driver, 10).until(
        EC.presence_of_element_located((By.ID, 'grid_view_fromdate'))
    )
    time.sleep(1)
    date_field = context.driver.find_element(By.ID, 'grid_view_fromdate')
    date_field.clear()

    context.driver.find_element(By.ID, 'date_check').click()
    time.sleep(1)

    # Wait for an edit button to be clickable, then get it
    edit_button = WebDriverWait(context.driver, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'img[src*="update.png"]'))
    )

    # Scroll then click
    context.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edit_button)
    time.sleep(0.3)
    edit_button.click()
    time.sleep(1)


#@when('we clear the from date and search')# added by shafee
#def step_impl(context):
#    WebDriverWait(context.driver, 5).until(
#        EC.presence_of_element_located((By.ID, 'grid_view_fromdate'))
#    )
#    time.sleep(3)
#    date_field = context.driver.find_element(By.ID, 'grid_view_fromdate')
#    date_field.clear()
#
#
#    context.driver.find_element(By.ID, 'date_check').click()
#    time.sleep(3)
#
#    context.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edit_button)
#    time.sleep(3)
#
#    WebDriverWait(context.driver, 5).until(
#        EC.presence_of_element_located((By.CSS_SELECTOR, 'img[src*="update.png"]'))
#    )
#
#    edit_button = context.driver.find_elements(By.CSS_SELECTOR, 'img[src*="update.png"]')[0]
#    edit_button.click()
#    time.sleep(3)




#@given('we select "{text}" in "{field_id}" autocomplete')
#@when('we select "{text}" in "{field_id}" autocomplete')
#@then('we select "{text}" in "{field_id}" autocomplete')
#def select_autocomplete(context, text, field_id):
#    try:
#        autocomplete = context.driver.find_element(By.ID, 'ac_orders_model_' + field_id + '_ac') 
#        autocomplete = context.driver.find_element(By.ID, 'ac_' + context.form_prefix + field_id + '_ac')  
#        autocomplete.send_keys(text)
#        script = f"""
#            setLazyAutoCompleteValueFromText('{'ac_orders_model_' + field_id + '_ac'}', '{'orders_model_' + field_id + '_ac'}');
#        """
#        # Execute the JavaScript
#        context.driver.execute_script(script)
#    except:
#       autocomplete = context.driver.find_element(By.ID, 'orders_model_' + field_id)
#        autocomplete.send_keys(text)
#
#        autocomplete = context.driver.find_element(By.ID, 'orders_model_' + field_id)
#        autocomplete.send_keys(text)
#        menu = context.driver.find_element(By.CSS_SELECTOR, '.ui-autocomplete[style$="display: block;"]')
#        mover = ActionChains(context.driver)
#        mover.move_to_element(menu).perform()
#        context.driver.execute_script("window.scrollBy(0, 100);")
#        menu.click()

@given('we select "{text}" in "{field_id}" autocomplete')
@when('we select "{text}" in "{field_id}" autocomplete')
@then('we select "{text}" in "{field_id}" autocomplete')
def select_autocomplete(context, text, field_id):
    try:
        # Autocomplete field with dynamic prefix
        autocomplete = context.driver.find_element(By.ID, 'ac_' + context.form_prefix + field_id + '_ac')
        
        
        autocomplete.send_keys(text)
        
        script = f"""
            setLazyAutoCompleteValueFromText('ac_{context.form_prefix}{field_id}_ac', '{context.form_prefix}{field_id}_ac'); 
        """
         

        context.driver.execute_script(script)

    except NoSuchElementException:
        # Fallback: normal input field with dynamic prefix
        autocomplete = context.driver.find_element(By.ID, context.form_prefix + field_id)
        
        autocomplete.send_keys(text)
       
        menu = context.driver.find_element(By.CSS_SELECTOR,'.ui-menu-item')
        mover = ActionChains(context.driver)
        mover.move_to_element(menu).perform()
        context.driver.execute_script("window.scrollBy(0, 100);")
        menu.click()
# by shafee

# @given('we select "{text}" in "{field_id}" autocomplete')
# @when('we select "{text}" in "{field_id}"  autocomplete')
# @then('we select "{text}" in "{field_id}"  autocomplete')
# def select_autocomplete(context, text, field_id):
#     try:
#         # Autocomplete field with dynamic prefix
#         autocomplete = context.driver.find_element(By.ID, 'ac_' + context.form_prefix + field_id + '_ac')
#         autocomplete.send_keys(text)
        
#         script = f"""
#             setLazyAutoCompleteValueFromText('ac_{context.form_prefix}{field_id}_ac', '{context.form_prefix}{field_id}_ac');
#         """
#         context.driver.execute_script(script)

#     except NoSuchElementException:
#         # Fallback: normal input field with dynamic prefix
#         autocomplete = context.driver.find_element(By.ID, context.form_prefix + field_id)
#         autocomplete.send_keys(text)
        
#         menu = context.driver.find_element(By.CSS_SELECTOR, '.ui-autocomplete[style$="display: block;"]')
#         mover = ActionChains(context.driver)
#         mover.move_to_element(menu).perform()
#         context.driver.execute_script("window.scrollBy(0, 100);")
#         menu.click()

        
#@given('we enter "{value}" in "{field}"')
#@when('we enter "{value}" in "{field}"')
#def enter_value(context, value, field):
#    autocomplete = context.driver.find_element(By.ID, 'orders_model_' + field)
#    autocomplete.clear()
#    autocomplete.send_keys(value)


@given('we enter "{value}" in "{field}"')
@when('we enter "{value}" in "{field}"')
def enter_value(context, value, field):
    try:
        # First try direct ID match (since no prefix is used in this form)
        element = WebDriverWait(context.driver, 10).until(
            EC.element_to_be_clickable((By.ID, field)))
    except:
        try:
            # Fallback to name attribute
            element = WebDriverWait(context.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, field)))
        except Exception as e:
            context.driver.save_screenshot("enter_value_error.png")
            raise Exception(f"Could not find field '{field}' using ID or NAME")

    try:
        element.clear()
        element.send_keys(value)
    except:
        # JavaScript fallback
        context.driver.execute_script(f"arguments[0].value = '{value}';", element)

@given('we check "{field}"')
@when('we check "{field}"')
@then('we check "{field}"')
def check_checkbox(context, field):
    try:
        # Try ID first
        checkbox = WebDriverWait(context.driver, 10).until(
            EC.element_to_be_clickable((By.ID, field)))
    except:
        try:
            # Try name if ID fails
            checkbox = WebDriverWait(context.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, field)))
        except Exception as e:
            context.driver.save_screenshot("checkbox_error.png")
            time.sleep(8)
            raise Exception(f"Could not find checkbox '{field}' using ID or NAME")

    if not checkbox.is_selected():
        try:
            checkbox.click()
            time.sleep(8)
        except:
            # JavaScript fallback
            context.driver.execute_script("arguments[0].checked = true;", checkbox)
            time.sleep(8)#


@given('we fill the grid with')
@when('we fill the grid with')
@then('we fill the grid with')
def fill_grid(context):
    if not context.table:
        context.table = context.loaded_table
    grid_list = [list(row) for row in context.table]
    grid_list = json.dumps(grid_list)
    time.sleep(20)
    script = f"""
    // Define the importGridFromTestArray function
    async function importGridFromTestArray(data) {{
        data.unshift([]);
        var Chunk_num = 0;
        var len =[];
        var current_len = [];
        var previous_len = [];
        var i,j, temp, chunk = 1;
        runLoop = async () => {{
            for (i = 0,j = data.length; i < j; i += chunk) {{
                temp = data.slice(i, i + chunk);
                await new Promise(resolve => setTimeout(resolve, 100));
                len.push(temp.length);
                const length = len.reduce((partial_sum, a) => partial_sum + a, 0) - 1;
                Chunk_num++;
                if (Chunk_num < 1) {{
                    current_len.push(temp.length);
                }} else {{
                    previous_len.push(current_len);
                    current_len = [];
                    current_len.push(temp.length);
                }}
                eq = eval(previous_len.join('+'));
                csvTableChunk(temp, Chunk_num, length, eq);
                if (i === data.length - 1) {{
                    if (window.calculateTotal != null) {{
                        calculateTotal();
                    }}
                    return;
                }}
                if (window.calculateTotal != null) {{
                    calculateTotal();
                }}
            }}
        }}
        runLoop();
    }}

    importGridFromTestArray({grid_list});
    """
    print(script) 
    


    context.driver.execute_script(script)
    time.sleep(8)
    

@when('we click "Save" button')
def create_entry(context):
    context.driver.find_element(By.CLASS_NAME, 'createEntry').click()

@when('we force enable and click "Create" button')
def enable_and_click_create_button(context):
    btn = context.driver.find_element(By.ID, 'accounts-form-submit-button-clone')
    context.driver.execute_script("arguments[0].disabled = false;", btn)
    btn.click()


@given(u'we click button with id "{button_id}"')#shafee
def click_button_by_id(context, button_id):
    button = WebDriverWait(context.driver, 10).until(
        EC.element_to_be_clickable((By.ID, button_id))
    )
    button.click()
    time.sleep(1)

@when('we click "{text}" button')
def click_button_by_text(context, text):
    context.driver.find_element(By.CSS_SELECTOR, f'[value="{text}"]').click()
    time.sleep(20)

@given('we click "Show/hide Form" button')
def toggle_form(context):
    context.driver.find_element(By.CLASS_NAME, 'showHideForm').click()

@then('we should see success message')
def check_success_msg(context):
    try:
        context.driver.implicitly_wait(12)
        context.driver.find_element(By.CSS_SELECTOR, '.toast.toast-success')
        context.driver.implicitly_wait(12)
    except NoSuchElementException:
        assert False, f"Success message isn't displayed on the page."

@then('we should see this entry in grid:')
def check_grid_entry(context):
    if not context.table:
        context.table = context.loaded_table
    keys = context.table.headings
    values = list(context.table[0])

#@then(u'we should see the Chart of Accounts report')
#def step_impl(context):
#    from selenium.webdriver.common.by import By
#    from selenium.webdriver.support.ui import WebDriverWait
#    from selenium.webdriver.support import expected_conditions as EC
#
#    main_window = context.driver.current_window_handle

    # Wait for new window or tab
#    WebDriverWait(context.driver, 10).until(lambda d: len(d.window_handles) > 1)

#    windows = context.driver.window_handles
#    for window in windows:
#        if window != main_window:
#            context.driver.switch_to.window(window)
#            break

    # Wait for the PDF viewer page to load — wait for an element like toolbar or iframe
#    WebDriverWait(context.driver, 10).until(
#        EC.presence_of_element_located((By.TAG_NAME, "body"))
#    )

#    page_source = context.driver.page_source

    # Debug print if needed:
    # print(page_source)

#    assert "Chart of Accounts" in page_source, "Chart of Accounts report not found"

    # Close report window and switch back to main
    #context.driver.close()
    #context.driver.switch_to.window(main_window)


@then('the following fields should not be empty')
def check_fields_not_empty(context):
    for row in context.table:
        field_name = row['field']
        try:
            try:
                # First try locating the element by ID
                element = WebDriverWait(context.driver, 10).until(
                    EC.presence_of_element_located((By.ID, field_name))
                )
            except:
                # Fallback to NAME
                element = WebDriverWait(context.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, field_name))
                )

            value = element.get_attribute('value')
            #print(f"Captured Value for {field_name} => {value}")
            print(value)
            print(element)
            assert value.strip() != '', f"Field '{field_name}' is empty"

        except Exception as e:
            context.driver.save_screenshot(f"{field_name}_empty_check_error.png")
           # input(f"⚠️ Error encountered in {field_name}. Check browser and press Enter to continue...")
            raise AssertionError(f"Error checking field '{field_name}': {str(e)}")


                        



@when('we click edit button on "{page}" page')
def click_edit_button_with_retry(context, page):
    """
    Click edit button with retry logic and auto-refresh
    """
    try:
        # Navigate to the page first with retry logic
        page_url = f'https://{context.domain}/admin/?r={page}'
        if not navigate_to_page_with_retry(context.driver, page_url, 'title', timeout=10):
            raise Exception(f"Failed to navigate to {page} page")
        
        # Wait for edit button to be present and clickable
        edit_button = wait_for_element_with_auto_refresh(
            context.driver, 
            By.CSS_SELECTOR, 
            'img[src*="update.png"]', 
            timeout=10
        )
        
        if edit_button:
            edit_button.click()
            print(f"[PASS] Clicked edit button on {page} page")
            time.sleep(2)  # Wait for page to respond
        else:
            raise Exception("Edit button not found")
            
    except Exception as e:
        print(f"[FAIL] Failed to click edit button on {page} page: {e}")
        context.driver.save_screenshot(f"edit_button_fail_{page}.png")
        raise

@when('we wait for page to load with retry')
def wait_for_page_load_with_retry(context):
    """
    Wait for page to load with auto-refresh retry logic
    """
    try:
        wait_for_element_with_auto_refresh(context.driver, By.ID, 'title', timeout=10)
        print("[PASS] Page loaded successfully with retry")
    except Exception as e:
        print(f"[FAIL] Page load failed even after retry: {e}")
        raise



