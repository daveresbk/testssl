import socket

x = raw_input("\nPlease enter a domain name that you wish to translate: ")  

data = socket.gethostbyname_ex(x)
print ("\n\nThe IP Address of the Domain Name is: "+repr(data))  

x = raw_input("\nSelect enter to proceed back to Main Menu\n")  
if x == '1':   
    execfile('C:\python\main_menu.py')