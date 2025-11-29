# Start server in background job
$server_job = Start-Job -ScriptBlock { cd "C:\Users\Admin\Documents\Assignment Krafton"; python server.py }

# Wait for server to start
Start-Sleep -Seconds 3

# Run test
python test_assignment.py

# Clean up
Stop-Job -Job $server_job -PassThru | Remove-Job
