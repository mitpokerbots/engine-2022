'''
Encapsulates game and round state information for the player.
'''
from collections import namedtuple
from .actions import FoldAction, CallAction, CheckAction, RaiseAction
import random 

GameState = namedtuple('GameState', ['bankroll', 'game_clock', 'round_num'])
TerminalState = namedtuple('TerminalState', ['deltas', 'previous_state'])

FLOP_PERCENT = 0.1
TURN_PERCENT = 0.05
NUM_ROUNDS = 1000
STARTING_STACK = 400
BIG_BLIND = 2
SMALL_BLIND = 1



class RoundState(namedtuple('_RoundState', ['button', 'street', 'pips', 'stacks', 'hands', 'deck', 'previous_state'])):
    '''
    Encodes the game tree for one round of poker.
    '''

    def showdown(self):
        '''
        Compares the players' hands and computes payoffs.
        '''
        return TerminalState([0, 0], self)

    def legal_actions(self):
        '''
        Returns a set which corresponds to the active player's legal moves.
        '''
        active = self.button % 2
        continue_cost = self.pips[1-active] - self.pips[active]
        if continue_cost == 0:
            # we can only raise the stakes if both players can afford it
            bets_forbidden = (self.stacks[0] == 0 or self.stacks[1] == 0)
            return {CheckAction} if bets_forbidden else {CheckAction, RaiseAction}
        # continue_cost > 0
        # similarly, re-raising is only allowed if both players can afford it
        raises_forbidden = (continue_cost == self.stacks[active] or self.stacks[1-active] == 0)
        return {FoldAction, CallAction} if raises_forbidden else {FoldAction, CallAction, RaiseAction}

    def raise_bounds(self):
        '''
        Returns a tuple of the minimum and maximum legal raises.
        '''
        active = self.button % 2
        continue_cost = self.pips[1-active] - self.pips[active]
        max_contribution = min(self.stacks[active], self.stacks[1-active] + continue_cost)
        min_contribution = min(max_contribution, continue_cost + max(continue_cost, BIG_BLIND))
        return (self.pips[active] + min_contribution, self.pips[active] + max_contribution)

    def swap(self, player):
        '''
        Swaps players cards with a card from the deck.
        '''

        if random.random() < 0.5:
            random_card = random.choice(self.deck[1].cards)
            self.deck[1].cards.remove(random_card)
            #add the players card to the deck
            self.deck[1].cards.append(self.hands[player][0])
            self.hands[player] = [random_card, self.hands[player][1]]
        else:
            
            random_card = random.choice(self.deck[1].cards)
            self.deck[1].cards.remove(random_card)
            #add the players card to the deck
            self.deck[1].cards.append(self.hands[player][1])
            self.hands[player] = [self.hands[player][0], random_card]
    def proceed_street(self):
        '''
        Resets the players' pips and advances the game tree to the next round of betting.
        '''
        #river
        if self.street == 5:
            return self.showdown()

        #flop
        if self.street == 0:
            print(self.hands)
            if random.random() < FLOP_PERCENT:
                self.swap(0)
            if random.random() < FLOP_PERCENT:
                self.swap(1)
            new_street = 3
            return RoundState(1, new_street, [0, 0], self.stacks, self.hands, cards, self)

        #turn
        if self.street == 3:
            table = self.deck[0] + self.deck[1].deal(1)
            cards = (table, self.deck[1])
            if random.random() < TURN_PERCENT:
                self.swap(0)
            if random.random() < TURN_PERCENT:
                self.swap(1)
            new_street = self.street+1
            return RoundState(1, new_street, [0, 0], self.stacks, self.hands, cards, self)

        #river
        new_street = 3 if self.street == 0 else self.street + 1
        #update cards 
        table = self.deck[0] + self.deck[1].deal(1)
        cards = (table, self.deck[1])
        return RoundState(1, new_street, [0, 0], self.stacks, self.hands, cards, self)


    def proceed(self, action):
        '''
        Advances the game tree by one action performed by the active player.
        '''
        active = self.button % 2
        if isinstance(action, FoldAction):
            delta = self.stacks[0] - STARTING_STACK if active == 0 else STARTING_STACK - self.stacks[1]
            return TerminalState([delta, -delta], self)
        if isinstance(action, CallAction):
            if self.button == 0:  # sb calls bb
                return RoundState(1, 0, [BIG_BLIND] * 2, [STARTING_STACK - BIG_BLIND] * 2, self.hands, self.deck, self)
            # both players acted
            new_pips = list(self.pips)
            new_stacks = list(self.stacks)
            contribution = new_pips[1-active] - new_pips[active]
            new_stacks[active] -= contribution
            new_pips[active] += contribution
            state = RoundState(self.button + 1, self.street, new_pips, new_stacks, self.hands, self.deck, self)
            return state.proceed_street()
        if isinstance(action, CheckAction):
            if (self.street == 0 and self.button > 0) or self.button > 1:  # both players acted
                return self.proceed_street()
            # let opponent act
            return RoundState(self.button + 1, self.street, self.pips, self.stacks, self.hands, self.deck, self)
        # isinstance(action, RaiseAction)
        new_pips = list(self.pips)
        new_stacks = list(self.stacks)
        contribution = action.amount - new_pips[active]
        new_stacks[active] -= contribution
        new_pips[active] += contribution
        return RoundState(self.button + 1, self.street, new_pips, new_stacks, self.hands, self.deck, self)
