import SudokuBoard
import Variable
import Domain
import Trail
import Constraint
import ConstraintNetwork
import time
import random
from math import sqrt

class BTSolver:

    # ==================================================================
    # Constructors
    # ==================================================================

    def __init__ ( self, gb, trail, val_sh, var_sh, cc ):
        self.network = ConstraintNetwork.ConstraintNetwork(gb)
        self.hassolution = False
        self.gameboard = gb
        self.trail = trail

        self.varHeuristics = var_sh
        self.valHeuristics = val_sh
        self.cChecks = cc
        self.loaded = False

        # new constructor
        self.recent_vars = []
        self.tournCCCalled = 0
        self.mrvCount = 0
        self.halfway = self.gameboard.N * self.gameboard.N / 2

    # ==================================================================
    # Consistency Checks
    # ==================================================================

    # Basic consistency check, no propagation done
    def assignmentsCheck ( self ):
        for c in self.network.getConstraints():
            if not c.isConsistent():
                return False
        return True

    """
        Part 1 TODO: Implement the Forward Checking Heuristic

        This function will do both Constraint Propagation and check
        the consistency of the network

        (1) If a variable is assigned then eliminate that value from
            the square's neighbors.

        Note: remember to trail.push variables before you assign them
        Return: a tuple of a dictionary and a bool. The dictionary contains all MODIFIED variables, mapped to their MODIFIED domain.
                The bool is true if assignment is consistent, false otherwise.
    """
    def forwardChecking ( self ):
        if self.recent_vars == []:
            return ({}, False)
        var = self.recent_vars[-1]
        
        if var is None:
            return ({}, True)
        return ({}, self.updateNeigborDomain(var))

    def updateNeigborDomain(self, var):
        assignment = var.getAssignment()
        neighbors = self.network.getNeighborsOfVariable(var)
        for neighbor in neighbors:
            if (assignment == neighbor.getAssignment()):
                return False
            #trail push for the modified neighbor
            # rm the assignment from the neighbor's domain
            if not (neighbor.isAssigned()):
                self.trail.push(neighbor)
                neighbor.removeValueFromDomain(assignment)
            if (neighbor.domain.size() <= 0):
                return False 
        return True

    # =================================================================
	# Arc Consistency
	# =================================================================
    def arcConsistency( self ):
        assignedVars = []
        for c in self.network.constraints:
            for v in c.vars:
                if v.isAssigned():
                    assignedVars.append(v)
        while len(assignedVars) != 0:
            av = assignedVars.pop(0)
            for neighbor in self.network.getNeighborsOfVariable(av):
                if neighbor.isChangeable and not neighbor.isAssigned() and neighbor.getDomain().contains(av.getAssignment()):
                    neighbor.removeValueFromDomain(av.getAssignment())
                    if neighbor.domain.size() == 1:
                        neighbor.assignValue(neighbor.domain.values[0])
                        assignedVars.append(neighbor)

    
    """
        Part 2 TODO: Implement both of Norvig's Heuristics

        This function will do both Constraint Propagation and check
        the consistency of the network

        (1) If a variable is assigned then eliminate that value from
            the square's neighbors.

        (2) If a constraint has only one possible place for a value
            then put the value there.

        Note: remember to trail.push variables before you assign them
        Return: a pair of a dictionary and a bool. The dictionary contains all variables 
		        that were ASSIGNED during the whole NorvigCheck propagation, and mapped to the values that they were assigned.
                The bool is true if assignment is consistent, false otherwise.
    """
    def norvigCheck ( self ):
        if self.recent_vars == []:
            return ({}, False)
        var = self.recent_vars[-1]
        if not self.updateNeigborDomain(var):
            return ({}, False)

        for c in self.network.getConstraints():
            for val in range(1, self.gameboard.N + 1):
                timesValAvailable = 0
                unassignedVars = []
                for vari in c.vars:
                    if vari.isAssigned() and vari.getAssignment() == val:
                        break
                    if not vari.isAssigned() and val in vari.getValues():
                        timesValAvailable += 1
                        unassignedVars.append(vari)
                if timesValAvailable == 1:
                    unassignedVars[0].assignValue(val)
                    self.trail.push(unassignedVars[0])
                    if not self.updateNeigborDomain(unassignedVars[0]):
                        return  ({}, False)    
        return ({}, True)

        

    """
         Optional TODO: Implement your own advanced Constraint Propagation

         Completing the three tourn heuristic will automatically enter
         your program into a tournament.
     """
    def getTournCC ( self ):
        self.tournCCCalled += 1
        
        if self.tournCCCalled < self.halfway:
            return self.forwardChecking()
        else:
            if self.tournCCCalled % 4 == 1:
                return self.singleSpotCheck()
            elif self.tournCCCalled % 4 == 3:
                return self.forwardChecking()
            else:
                return self.norvigCheck()
                

    def singleSpotCheck ( self ):
        if self.recent_vars == []:
            return ({}, False)
        var = self.recent_vars[-1]
        if not self.updateNeigborDomain(var):
            return ({}, False)

        relevant_constraints = self.network.getConstraintsContainingVariable(var)
        for c in relevant_constraints:
            unassigned_count = 0
            for v in c.vars:
                if not v.isAssigned():
                    unassigned_count += 1
            if unassigned_count == 1:
                # assign it
                for v in c.vars:
                    if not v.isAssigned():
                        v.assignValue(v.getValues()[0])
                        self.trail.push(v)
                        if not self.updateNeigborDomain(v):
                            return  ({}, False)
                        break

        return ({}, True)

    # ==================================================================
    # Variable Selectors
    # ==================================================================

    # Basic variable selector, returns first unassigned variable
    def getfirstUnassignedVariable ( self ):
        for v in self.network.variables:
            if not v.isAssigned():
                return v

        # Everything is assigned
        return None

    """
        Part 1 TODO: Implement the Minimum Remaining Value Heuristic

        Return: The unassigned variable with the smallest domain
    """
    def getMRV ( self ):
        unassigned_variables = [v for v in self.network.getVariables() if not v.isAssigned()]
        if not unassigned_variables:
            return None

        mrv_variable = min(unassigned_variables, key=lambda v: v.getDomain().size())
        return mrv_variable

    """
        Part 2 TODO: Implement the Minimum Remaining Value Heuristic
                       with Degree Heuristic as a Tie Breaker

        Return: The unassigned variable with the smallest domain and affecting the most unassigned neighbors.
                If there are multiple variables that have the same smallest domain with the same number of unassigned neighbors, add them to the list of Variables.
                If there is only one variable, return the list of size 1 containing that variable.
    """
    def MRVwithTieBreaker ( self ):
        unassignedVariables = [v for v in self.network.getVariables() if not v.isAssigned()]
        if not unassignedVariables:
            return [None]

        # sort with tiebreaker
        sortedVariables = min(unassignedVariables, key=lambda v: (v.getDomain().size())) 
        minMrv = sortedVariables.getDomain().size()
        tiedSet = [n for n in unassignedVariables if minMrv == n.getDomain().size()] 
        if len(tiedSet) == 1:
             # one var
            return [sortedVariables]
        tieBreakerByNeighbors = min(tiedSet, key = lambda v: (-self.getUnassignedNeighborsCount(v)))
        return [tieBreakerByNeighbors]
       

    def getUnassignedNeighborsCount(self, v):
        unassigned_neighbors = [n for n in self.network.getNeighborsOfVariable(v) if not n.isAssigned()]
        return len(unassigned_neighbors)

    """
         Optional TODO: Implement your own advanced Variable Heuristic

         Completing the three tourn heuristic will automatically enter
         your program into a tournament.
     """
    def getTournVar ( self ):
        self.mrvCount += 1
        if self.mrvCount % (sqrt(self.gameboard.N) - 2) ** 2 == 0:
            return self.MRVwithTieBreaker()[0]
        return self.getMRV()

    # ==================================================================
    # Value Selectors
    # ==================================================================

    # Default Value Ordering
    def getValuesInOrder ( self, v ):
        values = v.domain.values
        return sorted( values )

    """
        Part 1 TODO: Implement the Least Constraining Value Heuristic

        The Least constraining value is the one that will knock the least
        values out of it's neighbors domain.

        Return: A list of v's domain sorted by the LCV heuristic
                The LCV is first and the MCV is last
    """
    def getValuesLCVOrder ( self, v ):
        values = v.getValues()
        values.sort(key=lambda val: self.calculateLCVScore(v, val))
        return values

    def calculateLCVScore(self, v, value):
        constraining_count = 0
        neighbors = self.network.getNeighborsOfVariable(v)

        for neighbor in neighbors:
            if not neighbor.isAssigned():
                neighbor_domain = neighbor.getDomain()
                if value in neighbor_domain.values:
                    constraining_count += 1

        return constraining_count


    """
         Optional TODO: Implement your own advanced Value Heuristic

         Completing the three tourn heuristic will automatically enter
         your program into a tournament.
     """
    def getTournVal ( self, v ):
        return self.getValuesLCVOrder (v) 

    # ==================================================================
    # Engine Functions
    # ==================================================================

    def solve ( self, time_left=600):
        if time_left <= 60:
            return -1

        start_time = time.time()
        if self.hassolution:
            return 0

        # Variable Selection
        v = self.selectNextVariable()
        # check if the assigment is complete
        if ( v == None ):
            # Success
            self.hassolution = True
            return 0

        # Attempt to assign a value
        for i in self.getNextValues( v ):

            # Store place in trail and push variable's state on trail
            self.trail.placeTrailMarker()
            self.trail.push( v )
            self.recent_vars.append(v)
            # Assign the value
            v.assignValue( i )
            # Propagate constraints, check consistency, recur
            if self.checkConsistency():
                elapsed_time = time.time() - start_time 
                new_start_time = time_left - elapsed_time
                if self.solve(time_left=new_start_time) == -1:
                    return -1
                
            # If this assignment succeeded, return
            if self.hassolution:
                return 0

            # Otherwise backtrack
            self.trail.undo()
            self.recent_vars.pop()
        return 0

    def checkConsistency ( self ):
        if not self.loaded:
            self.loaded = True
            for v in self.network.getVariables():
                if not v.isChangeable():
                    assignment = v.getAssignment()
                    neighbors = self.network.getNeighborsOfVariable(v)
                    for neighbor in neighbors:

                        if not (neighbor.isAssigned()):
                            neighbor.removeValueFromDomain(assignment)
                        if (neighbor.domain.size() == 0):
                            return ({}, False) 
        if self.cChecks == "forwardChecking":
            return self.forwardChecking()[1]

        if self.cChecks == "norvigCheck":
            return self.norvigCheck()[1]

        if self.cChecks == "tournCC":
            return self.getTournCC()

        else:
            return self.assignmentsCheck()

    def selectNextVariable ( self ):
        if self.varHeuristics == "MinimumRemainingValue":
            return self.getMRV()

        if self.varHeuristics == "MRVwithTieBreaker":
            return self.MRVwithTieBreaker()[0]

        if self.varHeuristics == "tournVar":
            return self.getTournVar()

        else:
            return self.getfirstUnassignedVariable()

    def getNextValues ( self, v ):
        if self.valHeuristics == "LeastConstrainingValue":
            return self.getValuesLCVOrder( v )

        if self.valHeuristics == "tournVal":
            return self.getTournVal( v )

        else:
            return self.getValuesInOrder( v )

    def getSolution ( self ):
        return self.network.toSudokuBoard(self.gameboard.p, self.gameboard.q)
