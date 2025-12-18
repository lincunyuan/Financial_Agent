<#
Database Services Startup Script

This script starts MySQL and Redis services on Windows.
Requires administrator privileges to run.

Usage:
1. Right-click the script and select "Run as administrator"
2. The script will automatically start both services
3. For MySQL, it will also attempt to log in automatically
4. For Redis, it will verify the connection and authentication

Configuration:
- Edit the values below to match your installation paths and credentials
#>

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "⚠ Running without Administrator privileges" -ForegroundColor Yellow
    Write-Host "  MySQL service management will be limited" -ForegroundColor Yellow
    Write-Host "  Redis can still be started as a standalone process" -ForegroundColor Yellow
    Write-Host "  For full functionality, run as Administrator" -ForegroundColor Yellow
    Write-Host
}

# Configuration settings
$mysqlPath = "D:\program\mysql-9.5.0-winx64"
$redisPath = "D:\program\redis"
$mysqlServiceName = "MySQL9.5"
$mysqlUsername = "root"
$mysqlPassword = "lincy123"
$redisPassword = "123"

Write-Host "=== Database Services Startup Script ===" -ForegroundColor Cyan

# Function to start MySQL service and connect
function Start-MySQL {
    Write-Host "Starting MySQL..." -ForegroundColor Yellow
    
    try {
        # First, verify MySQL service exists
        Write-Host "Verifying MySQL service exists..." -ForegroundColor Yellow
        $serviceExists = Get-Service -Name $mysqlServiceName -ErrorAction SilentlyContinue
        
        if (-not $serviceExists) {
            Write-Host "⚠ MySQL service '$mysqlServiceName' not found!" -ForegroundColor Yellow
            Write-Host "  1. Check if MySQL is installed correctly" -ForegroundColor Yellow
            Write-Host "  2. Run 'sc query' to see available services" -ForegroundColor Yellow
            return
        }
        
        # Check current service status
        if ($serviceExists.Status -eq 'Running') {
            Write-Host "✓ MySQL service is already running" -ForegroundColor Green
        } else {
            if ($isAdmin) {
                # Start MySQL service using net start
                Write-Host "Starting MySQL service..." -ForegroundColor Yellow
                $serviceResult = net start $mysqlServiceName 2>&1
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✓ MySQL service started successfully" -ForegroundColor Green
                } else {
                    Write-Host "✗ Failed to start MySQL service: $serviceResult" -ForegroundColor Red
                    Write-Host "  1. Check if service name '$mysqlServiceName' is correct" -ForegroundColor Yellow
                    Write-Host "  2. Check MySQL service properties in Services.msc" -ForegroundColor Yellow
                    return
                }
            } else {
                Write-Host "⚠ Cannot start MySQL service without Administrator privileges" -ForegroundColor Yellow
                Write-Host "  Service is in '$($serviceExists.Status)' state" -ForegroundColor Yellow
                Write-Host "  Please run as Administrator to start the service" -ForegroundColor Yellow
                return
            }
        }
        
        # Navigate to MySQL directory
        Set-Location $mysqlPath
        
        # Verify mysql client exists
        if (Test-Path ".\bin\mysql.exe") {
            # Attempt automatic login with full path
            Write-Host "Attempting MySQL login..." -ForegroundColor Yellow
            $mysqlClient = ".\bin\mysql.exe"
            $mysqlArgs = "-u $mysqlUsername -p$mysqlPassword"
            Start-Process $mysqlClient -ArgumentList $mysqlArgs -Wait -NoNewWindow
            
            Write-Host "✓ MySQL login session ended" -ForegroundColor Green
        } else {
            Write-Host "⚠ MySQL client not found in $mysqlPath\bin\" -ForegroundColor Yellow
            Write-Host "  Skipping login attempt" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Detailed error: $($_.Exception)" -ForegroundColor Red
    }
}

# Function to start Redis server and verify
function Start-Redis {
    Write-Host "`nStarting Redis..." -ForegroundColor Yellow
    
    try {
        # Navigate to Redis directory
        Set-Location $redisPath
        
        # Verify Redis server executable exists
        if (-not (Test-Path ".\redis-server.exe")) {
            Write-Host "✗ Redis server not found in $redisPath" -ForegroundColor Red
            Write-Host "  Check if Redis is installed correctly" -ForegroundColor Yellow
            return
        }
        
        # Verify Redis CLI exists
        if (-not (Test-Path ".\redis-cli.exe")) {
            Write-Host "✗ Redis CLI not found in $redisPath" -ForegroundColor Red
            Write-Host "  Cannot test connection without redis-cli.exe" -ForegroundColor Yellow
            return
        }
        
        # Check if Redis is already running
        Write-Host "Checking if Redis is already running..." -ForegroundColor Yellow
        $redisCommand = ".\redis-cli.exe -h localhost -p 6379 -a $redisPassword ping"
        $redisResponse = Invoke-Expression $redisCommand 2>&1
        
        if ($redisResponse -eq "PONG") {
            Write-Host "✓ Redis server is already running and authenticated" -ForegroundColor Green
            return
        }
        
        # Start Redis server in background
        Write-Host "Starting Redis server..." -ForegroundColor Yellow
        $redisProcess = Start-Process -FilePath ".\redis-server.exe" -WindowStyle Hidden -PassThru
        
        if ($redisProcess) {
            Write-Host "✓ Redis server process started (PID: $($redisProcess.Id))" -ForegroundColor Green
        } else {
            Write-Host "✗ Failed to start Redis server process" -ForegroundColor Red
            return
        }
        
        # Wait for server to initialize
        Write-Host "Waiting for Redis server to initialize..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
        
        # Test connection and authentication using user's specified command
        Write-Host "Testing Redis connection and authentication..." -ForegroundColor Yellow
        $redisResponse = Invoke-Expression $redisCommand 2>&1
        
        if ($redisResponse -eq "PONG") {
            Write-Host "✓ Redis server is running and authenticated successfully" -ForegroundColor Green
        } else {
            Write-Host "✗ Redis connection or authentication failed: $redisResponse" -ForegroundColor Red
            Write-Host "  1. Check if redis-server is running (PID: $($redisProcess.Id))" -ForegroundColor Yellow
            Write-Host "  2. Verify password '$redisPassword' is correct" -ForegroundColor Yellow
            Write-Host "  3. Check if Redis port 6379 is available" -ForegroundColor Yellow
            
            # Try to kill the process if it's running but not responding
            if ($redisProcess.HasExited -eq $false) {
                Write-Host "  Attempting to stop non-responsive Redis process..." -ForegroundColor Yellow
                Stop-Process -Id $redisProcess.Id -Force
            }
        }
        
    } catch {
        Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Detailed error: $($_.Exception)" -ForegroundColor Red
    }
}

# Function to verify both services are running
function Verify-AllServices {
    Write-Host "`n=== Verifying All Database Services ===" -ForegroundColor Cyan
    
    try {
        # Verify MySQL service
        Write-Host "Checking MySQL service..." -ForegroundColor Yellow
        $mysqlService = Get-Service -Name $mysqlServiceName -ErrorAction SilentlyContinue
        if ($mysqlService -and $mysqlService.Status -eq 'Running') {
            Write-Host "✓ MySQL service is running" -ForegroundColor Green
        } else {
            Write-Host "✗ MySQL service is not running" -ForegroundColor Red
        }
        
        # Verify Redis service
        Write-Host "Checking Redis service..." -ForegroundColor Yellow
        Set-Location $redisPath
        $redisCommand = ".\redis-cli.exe -h localhost -p 6379 -a $redisPassword ping"
        $redisResponse = Invoke-Expression $redisCommand 2>&1
        
        if ($redisResponse -eq "PONG") {
            Write-Host "✓ Redis server is running and responding" -ForegroundColor Green
        } else {
            Write-Host "✗ Redis server is not responding: $redisResponse" -ForegroundColor Red
        }
        
    } catch {
        Write-Host "✗ Verification error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main execution flow
Start-MySQL
Start-Redis

# Verify both services are running
Verify-AllServices

Write-Host "`n=== Startup Process Complete ===" -ForegroundColor Cyan
Write-Host "Press any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
