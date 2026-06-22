The user has just published a GitHub release for villheik/Rankaisijabot.

1. Check the status of the latest release pipeline:
   `gh run list --repo villheik/Rankaisijabot --workflow build.yml --limit 1`

2. If the pipeline is still in progress, wait and keep polling every 30 seconds using:
   `gh run watch --repo villheik/Rankaisijabot <run-id>`
   or by repeatedly running the list command. Inform the user that you are waiting.

3. If the pipeline fails, report the failure and stop — do not run the Watchtower command.

4. If the pipeline succeeds, run:
   `ssh raspi docker exec watchtower /watchtower --run-once`
   and report the result to the user.
