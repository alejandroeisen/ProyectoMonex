# Project Idea

## What is it?
Website/URL for internal company use. Displays data (Market information like stocks, exchange rates, etc) currently on an excel sheet to have ease of access when outside the office

## Who is it for?
Internal team usage. No access from outside

## The problem it solves
Access to information from outside the office

## Core features
<!-- List the must-have features for a first version -->
- Data is dynamic. It must be able to constantly fetch the data that is currently sitting on an excel spreadsheet that is being automatically updated with an API.
- 
- 

## Nice to have (later)
<!-- Features you want eventually but not in v1 -->
- BI features
- 

## Tech preferences
<!-- Any languages, frameworks, or tools you want to use? -->
<!-- If you have no preference, write "no preference" and Claude Code will suggest something -->
- Language: No preference
- Framework: No preference
- Database: No preference
- Other: No preference

## How it runs
<!-- e.g., web app, CLI tool, desktop app, API, browser extension, background service -->
Probably web app but unsure for now on best practices
## Any constraints or important details
<!-- e.g., must work offline, no paid APIs, keep dependencies minimal, needs auth, etc. -->
- Security: Must be secure access to the website as it will contain personal information. Either not on public internet and connection only through VPNs or secure authentication methods (like a landing page that only contains fields for ID+password and then it leads to actual website)
## Rough user flow
<!-- Optional but helpful: describe what a user does step by step -->
<!-- e.g., User opens app → logs in → sees dashboard → ... -->
- User logs in, Selects table he wants to view, table has columns and filtering options