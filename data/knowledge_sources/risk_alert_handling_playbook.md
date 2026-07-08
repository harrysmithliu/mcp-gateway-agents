# Risk Alert Handling Playbook

## Purpose
This playbook describes how operators handle alerts created from account investigation, risk scoring, and surveillance review workflows.

## Alert Intake
When a new alert is created, the operator should confirm:
- account identity
- alert severity
- summary context
- linked investigation evidence
- recent related alerts

## Status Lifecycle
Supported alert statuses include:
- open
- in_review
- escalated
- closed

## Operator Actions
For an alert in review, the operator should:
1. verify the underlying account overview
2. inspect recent trading activity
3. review risk profile changes and alert history
4. document the decision and update the alert status

## Escalation Rules
An alert should be escalated when severity is high, evidence is incomplete, or suspicious activity remains unresolved after operator review.

## Audit Expectations
Every status transition should be traceable through audit events and linked operational records.