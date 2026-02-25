If the output does not include concrete code modifications for every identified issue, the task is considered incomplete.
--------------------------------------
STRICT MODIFICATION OUTPUT RULES
The agent MUST NOT return vague modification suggestions.
For every affected file:
IF only a few lines change:
•	Show the exact modified lines
•	Include 5 lines of context above and below
•	Use clear BEFORE / AFTER blocks
IF multiple sections of a file change OR structural changes occur:
•	Provide the complete modified file content
•	Do not omit unchanged sections
If a file is deleted:
•	Explicitly state it is removed
If a file is created:
•	Provide full file content
Do NOT:
•	Say “apply similar changes elsewhere”
•	Say “update accordingly”
•	Provide conceptual instructions without code
•	Omit context
•	Return partial edits without clarity
The result must be directly applicable without guessing.