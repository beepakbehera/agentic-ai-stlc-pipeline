*** Settings ***
Documentation     Saucedemo login validation - all user personas.
...               Generated for the Agentic STLC pipeline (Agent 2 output,
...               selectors healed by Agent 2b). Runs with robotframework-browser.
Library           Browser
Suite Setup       Open Login Page
Suite Teardown    Close Browser

*** Variables ***
${BASE_URL}       https://www.saucedemo.com/
${PASSWORD}       secret_sauce

*** Test Cases ***
Valid Login As standard_user
    [Tags]    smoke    critical
    Fill Credentials    standard_user    ${PASSWORD}
    Submit Login
    Wait For Url    *inventory.html
    Get Title    ==    Swag Labs
    Logout Via Menu

locked_out_user Is Blocked With Epic Sadface
    [Tags]    negative
    Fill Credentials    locked_out_user    ${PASSWORD}
    Submit Login
    Get Text    [data-test="error"]    contains    locked out

Invalid Password Shows Error
    [Tags]    negative
    Fill Credentials    standard_user    wrong_password
    Submit Login
    Get Text    [data-test="error"]    contains    Username and password do not match

problem_user Sees Inventory After Login
    [Tags]    personas
    Fill Credentials    problem_user    ${PASSWORD}
    Submit Login
    Wait For Url    *inventory.html
    Logout Via Menu

error_user Sees Inventory After Login
    [Tags]    personas
    Fill Credentials    error_user    ${PASSWORD}
    Submit Login
    Wait For Url    *inventory.html
    Logout Via Menu

visual_user Sees Inventory After Login
    [Tags]    personas
    Fill Credentials    visual_user    ${PASSWORD}
    Submit Login
    Wait For Url    *inventory.html
    Logout Via Menu

performance_glitch_user Logs In Despite Delay
    [Tags]    personas    performance
    Fill Credentials    performance_glitch_user    ${PASSWORD}
    Submit Login
    Wait For Url    *inventory.html    timeout=30s
    Logout Via Menu

*** Keywords ***
Open Login Page
    New Browser    chromium    headless=True
    New Page
    Go To    ${BASE_URL}
    Wait For Elements State    css=#login-button    visible

Fill Credentials
    [Arguments]    ${username}    ${password}
    Fill Text    css=#user-name    ${username}
    Fill Text    css=#password    ${password}

Submit Login
    Click    css=#login-button

Logout Via Menu
    Click    css=#react-burger-menu-btn
    Click    css=#logout_sidebar_link
    Wait For Elements State    css=#login-button    visible
