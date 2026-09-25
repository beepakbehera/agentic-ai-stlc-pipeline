*** Settings ***
Documentation     Common Robot Framework Keywords for Web Testing
...               Shared utilities for all test suites

Library           Browser
Library           Collections
Library           String
Library           OperatingSystem

*** Variables ***
${DEFAULT_TIMEOUT}    30s
${SHORT_TIMEOUT}      5s

*** Keywords ***

# =============================================================================
# Browser Management
# =============================================================================

Open Browser With Config
    [Arguments]    ${browser}=${BROWSER}    ${headless}=${HEADLESS}    ${viewport_width}=1280    ${viewport_height}=720
    New Browser    ${browser}    headless=${headless}
    New Context    viewport={'width': ${viewport_width}, 'height': ${viewport_height}}
    New Page
    Set Test Variable    ${PAGE}    ${EXECUTION_CONTEXT}.page

Close All Browsers
    Close Browser    all

# =============================================================================
# Navigation
# =============================================================================

Go To URL
    [Arguments]    ${url}
    Go To    ${url}
    Wait For Load State    networkidle

Reload Page
    Reload
    Wait For Load State    networkidle

Go Back
    Go Back
    Wait For Load State    networkidle

Go Forward
    Go Forward
    Wait For Load State    networkidle

# =============================================================================
# Element Interactions
# =============================================================================

Click Element
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Click    ${locator}    timeout=${timeout}

Fill Field
    [Arguments]    ${locator}    ${text}    ${timeout}=${DEFAULT_TIMEOUT}
    Fill    ${locator}    ${text}    timeout=${timeout}

Type Text
    [Arguments]    ${locator}    ${text}    ${timeout}=${DEFAULT_TIMEOUT}
    Type    ${locator}    ${text}    timeout=${timeout}

Clear And Fill
    [Arguments]    ${locator}    ${text}    ${timeout}=${DEFAULT_TIMEOUT}
    Clear    ${locator}
    Fill    ${locator}    ${text}    timeout=${timeout}

Press Key
    [Arguments]    ${locator}    ${key}    ${timeout}=${DEFAULT_TIMEOUT}
    Press    ${locator}    ${key}    timeout=${timeout}

Hover Element
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Hover    ${locator}    timeout=${timeout}

Select Dropdown
    [Arguments]    ${locator}    ${value}    ${timeout}=${DEFAULT_TIMEOUT}
    Select    ${locator}    ${value}    timeout=${timeout}

Check Checkbox
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Check    ${locator}    timeout=${timeout}

Uncheck Checkbox
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Uncheck    ${locator}    timeout=${timeout}

# =============================================================================
# Assertions
# =============================================================================

Element Should Be Visible
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=visible    timeout=${timeout}

Element Should Be Hidden
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=hidden    timeout=${timeout}

Element Should Contain Text
    [Arguments]    ${locator}    ${expected_text}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=visible    timeout=${timeout}
    ${actual_text}=    Get Text    ${locator}
    Should Contain    ${actual_text}    ${expected_text}

Element Should Not Contain Text
    [Arguments]    ${locator}    ${unexpected_text}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=visible    timeout=${timeout}
    ${actual_text}=    Get Text    ${locator}
    Should Not Contain    ${actual_text}    ${unexpected_text}

Element Should Have Attribute
    [Arguments]    ${locator}    ${attribute}    ${expected_value}=    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=attached    timeout=${timeout}
    ${actual_value}=    Get Attribute    ${locator}    ${attribute}
    Should Be Equal    ${actual_value}    ${expected_value}

Element Should Be Enabled
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=attached    timeout=${timeout}
    ${is_enabled}=    Get Property    ${locator}    disabled
    Should Be False    ${is_enabled}

Element Should Be Disabled
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=attached    timeout=${timeout}
    ${is_enabled}=    Get Property    ${locator}    disabled
    Should Be True    ${is_enabled}

Page Should Contain Element
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=attached    timeout=${timeout}

Page Should Not Contain Element
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=detached    timeout=${timeout}

# =============================================================================
# Waiting
# =============================================================================

Wait For Element Visible
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=visible    timeout=${timeout}

Wait For Element Hidden
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element    ${locator}    state=hidden    timeout=${timeout}

Wait For Network Idle
    [Arguments]    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Network Idle    timeout=${timeout}

Wait For Load State
    [Arguments]    ${state}=networkidle    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Load State    ${state}    timeout=${timeout}

# =============================================================================
# Screenshots & Artifacts
# =============================================================================

Take Screenshot
    [Arguments]    ${name}=screenshot    ${full_page}=True
    ${timestamp}=    Get Time    result_format=timestamp
    ${filename}=    Set Variable    ${name}_${timestamp}.png
    Take Screenshot    ${filename}    full_page=${full_page}
    [Return]    ${filename}

Take Element Screenshot
    [Arguments]    ${locator}    ${name}=element_screenshot
    ${timestamp}=    Get Time    result_format=timestamp
    ${filename}=    Set Variable    ${name}_${timestamp}.png
    Take Element Screenshot    ${locator}    ${filename}
    [Return]    ${filename}

# =============================================================================
# JavaScript Execution
# =============================================================================

Execute JavaScript
    [Arguments]    ${script}    @{args}
    ${result}=    Execute Javascript    ${script}    ${args}
    [Return]    ${result}

Execute Async JavaScript
    [Arguments]    ${script}    @{args}
    ${result}=    Execute Async Javascript    ${script}    ${args}
    [Return]    ${result}

# =============================================================================
# Data Handling
# =============================================================================

Generate Random String
    [Arguments]    ${length}=10    ${charset}=alphanumeric
    ${random}=    Generate Random String    ${length}    ${charset}
    [Return]    ${random}

Generate Random Email
    [Arguments]    ${prefix}=test    ${domain}=example.com
    ${random}=    Generate Random String    8    alphanumeric
    ${email}=    Set Variable    ${prefix}_${random}@${domain}
    [Return]    ${email}

Get Current Timestamp
    [Arguments]    ${format}=%Y%m%d_%H%M%S
    ${timestamp}=    Get Time    result_format=${format}
    [Return]    ${timestamp}

# =============================================================================
# Error Handling
# =============================================================================

Run Keyword And Capture Screenshot On Failure
    [Arguments]    ${keyword}    @{args}
    Run Keyword And Return Status    ${keyword}    @{args}
    Run Keyword If    not ${EXECUTION_STATUS}    Take Screenshot    failure_${keyword}
    [Return]    ${EXECUTION_STATUS}

Retry Keyword
    [Arguments]    ${times}=3    ${interval}=2s    ${keyword}    @{args}
    :FOR    ${i}    IN RANGE    ${times}
    \    ${status}=    Run Keyword And Return Status    ${keyword}    @{args}
    \    Run Keyword If    ${status}    Exit For Loop
    \    Sleep    ${interval}
    Run Keyword If    not ${status}    Fail    Keyword failed after ${times} attempts