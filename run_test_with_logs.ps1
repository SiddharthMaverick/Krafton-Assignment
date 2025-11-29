# Start server in background job with output captured
$server_job = Start-Job -ScriptBlock { 
    cd "C:\Users\Admin\Documents\Assignment Krafton"
    python server.py 2>&1 | Tee-Object -FilePath "server_output.txt"
}

# Wait for server to start
Start-Sleep -Seconds 3

# Run test  
python test_assignment.py 2>&1

# Clean up
Stop-Job -Job $server_job -PassThru | Remove-Job

# Show server output
Write-Host "`n=== SERVER OUTPUT ===" -ForegroundColor Cyan
Get-Content "server_output.txt" -Tail 100
