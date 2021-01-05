===============================
TUTORIAL
===============================
A brief guide to help you use and understand version 1.

Once you have completed all applicable steps in `Quick Start <QS>`_ run the application and wait for it to open. The main window will pop up and look like the following:
    
.. image:: ../fotos/S1.png
*(Figure 1)*

--------------------
1. Navigation Bar
--------------------
Here you will find all of the necessary utilities and information to use this application. 

* File: you’ll find commands to help edit some settings, load or save your canvas, export your work or exit the application. The application will save files to and load files from the directory in which your app is found. To change the settings (such as appearance of the platform) you must follow these steps:

    1. Select Help in the same Navigation Bar.
    2. Select Default Settings.
    3. Copy the setting(s) that you wish to change.

.. image:: ../fotos/S2.png
*(Figure 2)*

    4. Click File in the Navigation Bar
    5. Select Edit Settings
    6. Paste the copied settings to change.
    7. Change the values accordingly.

.. image:: ../fotos/S3.png
*(Figure 3)*

    8. Close both NotePads and Select File again. (Click save if you haven’t already saved them).
    9. Click Reload Settings or simply exit the application and open it again.

    To restore default settings simple erase all changes made under File -> Edit Settings so that it looks  like the following:

.. image:: ../fotos/S4.png
*(Figure 4)*

* Edit: you find basic commands like copy, paste, undo and redo, along with their keyboard shortcuts. 

* Select: you find some shortcuts to help you select parts of the canvas such as all of the nodes. Note that select all will select all nodes and reactions. These commands will select all of the indicated, regardless of the compartment the nodes or reactions are in.

* Reaction: provides quick options to generate your reactions. These help us select multiple nodes and name them as reactants or products rather than go one by one using the creating panel (explained below). 

* Plugins: you’ll find the main features that will help you create, visualize, or analyze your reactions. They will also appear in the applications menu under their corresponding sections. We will go over them in detail below, but you’ll have: Add Reaction, Arrow Designer, Auto Layout, Random Network and Structural Analysis.

-----------------
2. Applicaions Menu
-----------------

A lot of the functionalities found here are also in the Navigation Bar. However, they are organized according to their different uses, allowing you to access them in a more structured way.

* Main: We find Undo, Redo, Zoom in, and Zoom out.

* Analysis: We find Structural analysis, a function used is to calculate and visualize the stoichiometry matrix and conserved moieties for the network. When the user clicks on the “Compute Conservation Laws” button, the plugin will derive the stoichiometry matrix for the current network on canvas. It also computes any conserved moieties for the network. By selecting the moieties in the plugin, it can highlight the nodes on the network by changing their colors according to the user’s preference. Finally, unhighlighting the nodes is also possible by clicking the “Clear” button.

* Appearance: We have Arrow Designer. This allows you to personalize the arrows that appear in the reactions. A window will pop up where you will be able to move the circles to your desired visual. This will be implemented when you click Save. To restore the default arrow you may click arrow designer once again and click Restore Default.

* Utilities: Here you will find Add Reaction, Random Network, and Autolayout. 

  - Add Reaction: This allows you to add reactions choosing the type in a quick way. First you want to select all the nodes that you want as reactants and then select them as reactant on the panel on the left, then select your desired products, and again, click products on the left. Finally, you want to click the Add Reaction utility and simply choose which type of reaction you want these sets of products and reactants to form.

  - Random Network: This utility lets you create a completely random network with personalized parameters. **NOTE: This will erase your current canvas, not add to it. If you want to save your work you can do so under File in the Navigation Bar.** After You create the random network you will be able to modify it at your own will, including adding and deleting nodes. To customize the parameters:

    + Number of species: The number of nodes that you want featured in your network.

    + Number of reactions: The number of reactions you want to create from the given species.

    + Probabilities: The probability of each type of reaction being featured. These must add to 1.

    + Random Seed: The randomizing seed for the code. This is a setting you won’t need to worry about too much unless you purposely want a lot of different random networks with the same features.
  
.. image:: ../fotos/S5.png
*(Figure 5)*

  - Auto Layout: This utility automatically gives you a “nice” layout of your network. NOTE: This has not been implemented for multiple compartments, and doesn’t behave well for complex reactions. This is under work, and will be cleaned by version 2. The parameters:
    + Maximum number of iterations: This will help make the layout more neat. 100-120 is a good default value range. If you have a very high number of nodes then you’re going to want to increase this number. Computationally, it may take a bit longer when this number is increased by a lot.
    + K: must be a float (no decimals allowed). This represents (in a way) the distance between nodes. If the number of nodes isn’t very large this number won’t have a big impact. Anything between 60-100 is a reasonable default.
    + Scale of the layout: This will modify the extension that the layout will cover. Again, this will not affect the layout too much if it is very large or very small. 500-1000 is a reasonable range.


