from PIL import Image
from collections import deque
from random import shuffle
import io
unoDeck = []
discards = deque()
players = []
#playDirection = 1

def buildDeck()->list:
    """
    Generate UNO Deck of 108 Cards
    Param: None
    Returns: List
    """
    colors = ["R","G","Y","B"]
    values = list(range(10)) + ["+2","Skip","Reverse"]
    wilds = ["Wild","Wild +4"] * 4
    deck = [(color,value) for color in colors for value in values] * 2
    [deck.remove(item) for item in list(zip(colors,[0,0,0,0]))]
    deck = deck + wilds
    shuffle(deck)
    return deck

def initialize():
    """Sets up deck and discards for new game
    """
    global unoDeck
    global players
    global discards 
    unoDeck= buildDeck()
    for card in unoDeck:
        if str(type(card)) == "<class 'tuple'>" and card[1] not in ["+2","Skip","Reverse"]:
            discards.appendleft(unoDeck.pop(unoDeck.index(card)))
            break
 
def reset():
    """Resets Deck, Discards and Playerlist upon finishing and cancelling the game 
    """
    global unoDeck
    global players
    global discards
    unoDeck = []
    discards = deque()
    players = []
      
def startGame(self,players):
    playing = False
    if len(players) >= 2:
        playing = True
    else:
        print("not enough players")
    while playing:
        for player in players:
            if player.turn:
                if (len(player.canPlay()) > 0):
                    print("play card")
    
def drawCards(numCards):
    global unoDeck
    global discards
    if numCards > len(unoDeck):
        last_dsc = discards.popleft()
        discards = deque()
        discards.appendleft(last_dsc)
        unoDeck = buildDeck()
        unoDeck.remove(last_dsc)              
    return [unoDeck.pop() for x in range(numCards)]

class Player:
    def __init__(self,name,hand):
        self.name = name
        self.hand = hand           
        self.turn = False
        self.has_to_draw = False
        self.called_uno_already = False
    def showHand(self):
        i = 0
        x = len(self.hand)
        im = Image.open("assets/back.png")
        width,h = im.size
        im = Image.new("RGBA",(width*x,h),(250,250,250))
        for card in self.hand:
            if card in ["Wild","Wild +4"]:
                m=card.replace("ild","")
                im1 = Image.open(f"assets/{m}.png")
                im.paste(im1,(width*i,0))
                #im1.show()
            elif str(type(card) == "<class 'tuple'>"):
                background = Image.open(f"assets/{card[0]}.png")
                frontImage = Image.open(f"assets/{card[1]}.png")                
                background = background.convert("RGBA")
                frontImage = frontImage.convert("RGBA")
                background.paste(frontImage, mask=frontImage)
                im.paste(background,(width*i,0))
                #newim.show()
            i+=1
        #im.show()
        return image_to_byte_array(im)
    
    def canPlay(self):
        playable = [card for card in self.hand if card in ["Wild","Wild +4"] or card[0]==discards[0][0] or card[1]==discards[0][1] or card[0] in discards[0]]
        #playable.extend([card for card in self.hand if discards[0][0] in card])
        return playable  

def current_discard(wildcolor=""):
    """card on top of the discard heap 

    Args:
        wildcolor (str, optional): Chosen color of the wildcard if applicable. Defaults to "".

    Returns:
        Byte Array of Image: to be posted as file on discord
    """
    if "Wild" in discards[0] or "Wild +4" in discards[0]:
        a = discards[0]
        m=a.replace("ild","")
        return image_to_byte_array(Image.open(f"assets/{m}{wildcolor}.png"))
    else:
        bg = Image.open(f"assets/{discards[0][0]}.png")
        fr = Image.open(f"assets/{discards[0][1]}.png")
        bg= bg.convert("RGBA")
        fr= fr.convert("RGBA")
        bg.paste(fr,mask=fr)
        return (image_to_byte_array(bg))
        
def image_to_byte_array(image: Image) -> bytes:
    imgByteArr = io.BytesIO()
    image.save(imgByteArr, format="PNG")
    imgByteArr.seek(0)
    return imgByteArr


            
# initialize()    
# p1 = Player("1",drawCards(7))
# players.append(p1)
# #p1.showHand()
# print(p1.hand)
# print(discards)
# discards.appendleft("WildB")
# print(discards)
# print(p1.canPlay())