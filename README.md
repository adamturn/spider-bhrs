# Branch Hours Spider
Branch lobby hours data.
## [X] JPM

## [X] BAC

## [X] WFC

## PNC
The lowest we can get is city-level urls. So start with a list of city-level urls. Read the list from JSON. Keep an original copy.
After hitting the city-level url, we determine how many branches exist in the city, and iterate through the branch urls.
After extracting branch records from all branch urls in a city, the function call returns the list of city records to extend the final records list.
After exiting into the main function, extend the record list with new records. Next, pop the city-url you just hit from the list, then write the remaining city urls to disk.


## [X] RFC
HTML extract.