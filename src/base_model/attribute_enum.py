from enum import Enum, auto

class Attribute(Enum):
    """ 
    Base enum for all Attributes of entities in the model.
    For example, a case can have Attribute "STRAFFE", if it is a straffe case.
    And a judge can have a Attribute "STRAFFE", if the judge is able to be assigned straffe cases.
    
    This is meant to be as general and extendable as possible, because our own imaginations bottleneck the 
    amount of constraints we are able to formulate between the entities of the model.
    """
    
    # Case-Judge Attributes: 
    # case has type or judge can conduct cases of type
    CIVIL = auto() # bidirectional
    STRAFFE = auto() # bidirectional
    TVANG = auto() # bidirectional
    DOEDSBO = auto() # bidirectional
    GRUNDLOV = auto() # bidirectional
    
    # judge can only conduct short cases (<120min) due to health or case is <120 min
    SHORTDURATION = auto() # one-directional
    
    
    # Case-Room Attributes:
    # impeached is dangerous and requires security or room has facilities for security
    SECURITY = auto() # one-directional
    
    # virtual or physical room or case
    VIRTUAL = auto() # bidirectional
    
    
    # Judge-Room Attributes:
    # judge requires accessibility or room facilitates accessibility
    ACCESSIBILITY = auto() # one-directional
    
    def __str__(self):
        return self.name.capitalize()
    
    @classmethod
    def from_string(cls, attribute_string: str) -> 'Attribute':
        try:
            return cls[attribute_string.upper()]
        except KeyError:
            raise ValueError(f"No attribute found for: {attribute_string}")
        
    @classmethod
    def to_string(cls, attribute) -> str:
        if not isinstance(attribute, cls):
            raise ValueError(f"Expected an Attribute, got {type(attribute)}")
        return str(attribute)