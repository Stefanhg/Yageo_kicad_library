import os
defaultDeviceSet = []

for lines in open("deviceset_1206.txt", "r"): 
	defaultDeviceSet.append(lines)

def replaceInList(myList, OldValue, NewValue):
	newList = []
	# For every line, if line include OldValue, replace with NewValue
	for lines in myList:
		if(int(lines.find(OldValue)) + 1):
			lines = lines.replace(OldValue, NewValue)
		newList.append(lines)
	
	return(newList)

try:
	os.remove("_newLibParts.txt") # Removes the file
except:
	pass # File already removed
for lines in open("devicesets_resistors.txt", "r"): 
	currentValue = lines.rstrip()
	currentModifValue = currentValue

	print(currentModifValue)
	# Replaces the two value variabels
	newDeviceSet = replaceInList(defaultDeviceSet, "$VALUE$", currentModifValue)
	newDeviceSet = replaceInList(newDeviceSet, "$TrueVALUE$", currentValue)
	f = open("_newLibParts.txt", "a+")
	for lines in newDeviceSet:
		
		f.write(lines)
	f.close()
	


	