# Pie-Sculpt
Blender sculpting addon
Compatible Blender ver: 2.90+

1.Install Blender 2.90+

2.Go to edit preferences Addon and click [Install] and browse to where your 
  copy of pie_sculpt.py is and select it.

3.Use the ` accent grave key to access the pie menu once you are done press Enter/Return to finalize or
press Esc/Del/Backspace to delete item or cancel operation.

4.If you pick Add Mesh it adds a sub-d cube that you can use edit mode to further edit. Also x symmetry
is toggled on for quick mesh shaping. Once you have edited the mesh to your liking press enter to commit
to the changes and finalize the object. Rotation and scale are applied automatically when you commit.

5.If you pick Select Object it puts you into object mode and uses a raycast to highlight object under your
cursor. Left click on object it will select it and put you back into sculpt mode.


#Known issues: 
1. When first activating object select it will automatically pick an object then behave
as intended after that.
2. When trying to Undo directly after creating an object with the Mesh Add operator it appears
to be doing nothing i am actually blocking the undo behavior intentionally as this prevents a
100% crash with blenders undo system. Please press Esc/Del/Backspace to cancel your operators
it will do any cleanup for you auto-magically!

