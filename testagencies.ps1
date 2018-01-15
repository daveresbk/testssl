$externalserver = "http://35.196.231.95"

$readCsv = "c:\temp\agencias_traveltool_top10.csv"
$readLines = Import-Csv -Path $readCsv -Delimiter ';' -Header "domain","idagencia","application"
foreach ($line in $readLines) {
    $strRequest = "$externalserver/configuration?command=add&domain=$($line.domain)&idagencia=$($line.idagencia)&application=$($line.application)"
    write-host $strRequest
    
}