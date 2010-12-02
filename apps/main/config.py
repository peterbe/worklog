MAX_TITLE_LENGTH = 500
UNTAGGED_COLOR = "#4bb2c5"
TAG_COLOR_SERIES = ("#EAA228", "#c5b47f", "#579575", "#839557", "#958c12", 
                    "#953579", "#4b5de4", "#d8b83f", "#ff5800", "#0085cc", 
                    "#c747a3", "#cddf54", "#FBD178", "#26B4E3", "#bd70c7")

# This applies when it's not an all_day event and the date is the same                    
MINIMUM_DAY_SECONDS = 60 * 30                    
                    
API_CHANGELOG = (
  ("1.1", "Validation in place to prevent end date less than start date"),
  ("1.0", "Initial API launched"),
)
API_VERSION = API_CHANGELOG[0][0]
