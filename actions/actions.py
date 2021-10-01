# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import EventType, SlotSet, FollowupAction, AllSlotsReset

import datetime

ALLOWED_PIZZA_SIZES = ["broto", "média","grande", "família",]
ALLOWED_PIZZA_TOPS_S = ["4 queijos", "camarão", "calabresa", "atum", "frango"]
ALLOWED_PIZZA_TOPS_D = ["brigadeiro", "banana", "doce de leite"]
ALLOWED_PIZZA_TOPS = ALLOWED_PIZZA_TOPS_S + ALLOWED_PIZZA_TOPS_D
ALLOWED_DRINKS = ["refrigerante", "suco", "água", "água de coco"]

PRICES = {
    "broto": 10.0,
    "média": 15.0,
    "grande": 20.0,
    "família": 25.0,
    "salgado": 10.0,
    "doce": 20.0,
    "borda": 10.0,
    "entrega": 10.0,
    "bebida": 5.0
}


        
class ValidateOrderForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_order_form"

    def validate_size(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value.lower() not in ALLOWED_PIZZA_SIZES:
            dispatcher.utter_message(text=f"Só temos as opções: broto, média, grande ou família")
            return {"size": None}
        return {"size": slot_value.lower()}

    def validate_tops(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        tops = slot_value
        if type(slot_value) == Text:
            tops = [slot_value]
        if len(tops) > 4:
            dispatcher.utter_message(text=f"Desculpe, só servimos pizzas de até 4 sabores")
            return {"tops": None}
        for top in tops:
            if top.lower() not in ALLOWED_PIZZA_TOPS:
                dispatcher.utter_message(text=f"Desculpe, não temos a opção { top }, você pode escolher entre {'/'.join(ALLOWED_PIZZA_TOPS)}.")
                return {"tops": None}
        return {"tops": tops}


class ActionAddPizza(Action):
    def name(self) -> Text:
        return "action_add_pizza"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        pizzas = tracker.get_slot("pizzas")
        

        pizza = {
            "tops": tracker.get_slot("tops"),
            "size": tracker.get_slot("size"),
            "with_border": tracker.get_slot("border"),
            "price": 0.0
        }
        pizza['price'] += PRICES[pizza['size']]
        for top in pizza['tops']:
            if top in ALLOWED_PIZZA_TOPS_S:
                pizza['price'] += PRICES['salgado']
            elif top in ALLOWED_PIZZA_TOPS_D:
                pizza['price'] += PRICES['doce']
        if pizza['with_border']:
            pizza['price'] += PRICES['borda']
        pizzas.append(pizza)

        dispatcher.utter_message(f"Pizza de {'/'.join(pizza['tops'])} tamanho {pizza['size']} { 'com' if pizza['with_border'] else 'sem' } borda recheada, adicionada ao pedido. R${pizza['price']}")
        return [SlotSet("pizzas", pizzas)]

class ActionMorePizza(Action):

    def name(self) -> Text:
        return "action_more_pizza"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> List[Dict]:
        if len(tracker.get_slot("pizzas")) == 10:
            return [FollowupAction("drinks_form")]
        if tracker.get_intent_of_latest_message() == "affirm":
            return [
                SlotSet("tops", None),
                SlotSet("size", None),
                SlotSet("border", None),
                FollowupAction("order_form")
            ]
        elif tracker.get_intent_of_latest_message() == "deny":
            dispatcher.utter_message(text=f"Ok!")
            return []
        return []

class ValidateDrinksForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_drinks_form"

    async def required_slots(
        self,
        slots_mapped_in_domain: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Optional[List[Text]]:
        if tracker.get_slot("with_drinks"):
            return slots_mapped_in_domain + ["drink"]
        return slots_mapped_in_domain

    def validate_with_drinks(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if tracker.get_intent_of_latest_message() == "affirm" or tracker.get_intent_of_latest_message() == "order_drinks":
            return {"with_drinks": True}
        elif tracker.get_intent_of_latest_message() == "deny":
            dispatcher.utter_message(text=f"OK!")
            return {"with_drinks": False}
        else:
            return {"with_drinks": None}

    def validate_drink(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `bebidas` value."""
        drinks = slot_value
        if type(slot_value) == Text:
            drinks = [slot_value]
        for drink in drinks:
            if drink.lower() not in ALLOWED_DRINKS:
                dispatcher.utter_message(text=f"Desculpe, não temos {drink}, você pode escolher entre {'/'.join(ALLOWED_DRINKS)}.")
                return {"drink": None}
        return {"drink": slot_value}

class ValidateDeliveryForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_delivery_form"

    async def required_slots(
        self,
        slots_mapped_in_domain: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Optional[List[Text]]:
        if tracker.get_slot("delivery") == "entrega":
            return slots_mapped_in_domain + ["tip"]
        return slots_mapped_in_domain

    
    def extract_tip(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        if tracker.get_intent_of_latest_message() == "affirm":
            dispatcher.utter_message(text=f"Qual valor? Digite no formato '2,00' ")
            return {"tip": None}
        if tracker.get_intent_of_latest_message() == "deny":
            dispatcher.utter_message(text=f"Está bem, obrigado!")
            return {"tip": 0.0}
        if tracker.get_intent_of_latest_message() == "inform_tip":
            value = tracker.get_slot("tip").replace(",",".")
            value = float(value)
            dispatcher.utter_message(text=f"Agradecemos sua gorjeta.")
            return {"tip": value}
        return {"tip": None}

    # def validate_confirm_order(
    #     self,
    #     slot_value: Any,
    #     dispatcher: CollectingDispatcher,
    #     tracker: Tracker,
    #     domain: DomainDict,
    # ) -> Dict[Text, Any]:
    #     intent = tracker.latest_message['intent'].get('name')

    #     if intent == 'affirm':
    #         dispatcher.utter_message(text=f"Pedido enviado!")
    #         return {"confirm_order": True}
    #     else:
    #         dispatcher.utter_message(text=f"Pedido cancelado!")
    #         return {"confirm_order": False}
        
class ActionGreet(Action):

    def name(self) -> Text:
        return "action_greet"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
        ) -> List[Dict]:
 

        now = datetime.datetime.now()
        salutation = ""
        if 6 <= now.hour < 12:
            salutation = "Bom dia"
        elif 12 <= now.hour < 18:
            salutation = "Boa tarde"
        else:
            salutation = "Boa noite"
        if tracker.get_slot("salutation"):
            dispatcher.utter_message(
                f"{salutation}. Agradecemos seu retorno, no que posso lhe ajudar?"
            )
            return []
        
        dispatcher.utter_message(
            f"{salutation}. Seja bem vindo a Pizzaria do Elizandro, no que posso lhe ajudar?"
        )

        return [SlotSet("salutation", salutation)]


class AskForSlotAction(Action):
    def name(self) -> Text:
        return "action_ask_done_order"
    
    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        pizzas = tracker.get_slot("pizzas")
        drinks = tracker.get_slot("drink")
        with_drinks = tracker.get_slot("with_drinks")

        if type(drinks) == Text:
            drinks = [drinks]
        delivery = tracker.get_slot("delivery")
        tip = tracker.get_slot("tip")

        total_price = 0.0
        order = ""

        for pizza in pizzas:
           
            order += f"Pizza de {'/'.join(pizza['tops'])} tamanho {pizza['size']} { 'com' if pizza['with_border'] else 'sem' } borda recheada - R${pizza['price']}\n"
            total_price += pizza['price']

        if with_drinks:
            total_price += len(drinks) * PRICES['bebida']
        if delivery == "entrega":
            total_price += PRICES['entrega']
            total_price += tip

        dispatcher.utter_message(
            text=f""" Dados do pedido: \n
                    {order} \n 
                    {' '.join(drinks) if with_drinks else ''} 
                    \n{f'Tele-entrega: R$10.00 - Gorjeta: R${tip}' if delivery == 'entrega' else 'Retirar pedido na loja'}\n
                    valor total: R${total_price} \n
                    Posso confirmar seu pedido?""")

        return [
            SlotSet("total_price", total_price)
        ]

class ActionConfirmOrderValidator(FormValidationAction):
    def name(self) -> Text:
        return "validate_confirm_order_form"

    def validate_done_order(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
       
        if slot_value:
            dispatcher.utter_message(text=f"Pedido enviado!")
            return {"done_order": True}
        else:
            dispatcher.utter_message(text=f"Pedido cancelado!")
            return {"done_order": False}

class ActionClearOrder(Action):
    def name(self) -> Text:
        return "action_clear_order"
    
    def run(
            self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
        ) -> List[EventType]:
        return [
            SlotSet("tops", None),
            SlotSet("size", None),
            SlotSet("border", None),
            SlotSet("pizzas", []),
            SlotSet("done_order", None),
            SlotSet("drink", None),
            SlotSet("with_drinks", None),
            SlotSet("delivery", None),
            SlotSet("tip", None),
        ]

class CustomFallback(Action):
    def name(self) -> Text:
        return "action_custom_fallback"

    def run(self, dispatcher: CollectingDispatcher,tracker: Tracker,domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        count_error = int(tracker.get_slot("count_error"))
        count_error += 1
        if count_error == 3:
            dispatcher.utter_message("Estou tendo dificuldade para te entender, me chame novamente quando precisar. Até logo!")
            return[
                    SlotSet("count_error",str(0)),
                    AllSlotsReset()   
                ]

        dispatcher.utter_message(template="utter_please_rephrase")
        return [SlotSet("count_error",str(count_error))]