$externalserver = "http://213.130.43.119"

$readCsv = "c:\temp\traveltool\agencias_traveltool_top10.csv"
$readLines = Import-Csv -Path $readCsv -Delimiter ';' -Header "domain","idagencia","application"
foreach ($line in $readLines) {
    $strRequest = "$externalserver/configuration?command=add&domain=$($line.domain)&idagencia=$($line.idagencia)&application=$($line.application)"
    Write-Host "Remote call to: " $strRequest
    Invoke-WebRequest $strRequest
    
}