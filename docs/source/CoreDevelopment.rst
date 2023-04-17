=================================================
Core Development
=================================================

-----------------------------------------------------
How do I add a field to Node/Reaction/Compartment?
-----------------------------------------------------

1. In iodine.py, add the field in TNode/TReaction/TCompartment
  
  a. In iodine.py add getters & setters
  
  b. In iodine.py, update NodeSchema (or others) for serialization/deserialization

2. In data.py, add the field in Node/Reaction/Compartment. This is the data structure used to hold drawing information for the canvas

 You likely want to set a default value for this field.

3. In controller.py and mvc.py, add getters & setters that call iodine (mvc.py is the interface, controller.py is the implementation).

 Also update get_{node/reaction/compartment}_by_index(), which is a helper method that calls a bunch of getters to construct a Node (etc.) data structure. The data structure it returns is the class we modified in step 4.

4. [Optional] If you want this field exposed to the API, go to rkviewer.plugin/api.py and modify the NodeData/ReactionData/CompartmentData class and add the new field.

 a. Modify the _translate_*() function to account for the new field. This function translates Node → NodeData, etc.

 b. Update the “update_*()” function to include a parameter that allows modification of this field. Follow the existing conventions (e.g. default argument as None; only modify if the argument is not None, etc.)

5. [Optional] If you want this field to be modifiable in the form, go to forms.py and add the field in the corresponding NodeForm/ReactionForm/CompartmentForm class. Following the existing code for how to do this.

 a. You’ll need to create a control in CreateControls()

 b. The control should be bound to an event, which calls a callback function that updates the controller. Follow the other callback functions as examples.

 c. Also, to populate the form field based on the selected items, go to UpdateAllFields() and update that. You need to consider the cases where one item vs. multiple items are selected. There are existing helper functions that handle this, so check out how the other fields deal with this problem.

 d. Note: If the form freezes after changing the field, you might’ve gotten into a circular event loop, i.e. user changes field → event triggers → field updates controller → controller notifies form → form updates field → event triggers → … This shouldn’t happen with most controls (use ChangeValue()), but in case it does happen, check out the variable “_self_changes” and how it’s used.
 
Some additional work could definitely be done here to reduce the number of copies of the data classes and also to automate the process (e.g. of adding field to forms).
The MVC structure is also not perfect right now, with iodine importing from the view (e.g. Vec2). If a real MVC structure is deemed to be necessary,
work needs to be done to create a truly separate interface for models and views.
