##############################################################################
#
# Copyright (c) 2002 Nexedi SARL. All Rights Reserved.
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################

from Products.ZSQLCatalog.zsqlbrain import ZSQLBrain
from DateTime import DateTime
from ZTUtils import make_query

from Products.CMFCore.utils import getToolByName
from zLOG import LOG

class InventoryBrain(ZSQLBrain):
  """
    Global analysis (all variations and categories)
  """

  # Stock management
  def getInventory(self, at_date = None, ignore_variation=0, simulation_state=None, **kw):
    if type(simulation_state) is type('a'):
      simulation_state = [simulation_state]
    result = self.Resource_zGetInventory( resource_uid = [self.resource_uid],
                                          to_date=at_date, omit_simulation = 0,
                                          section_category = self.getPortalDefaultSectionCategory(),
                                          simulation_state=simulation_state)
    inventory = None
    if len(result) > 0:
      inventory = result[0].inventory
    if inventory is None:
      return 0.0
    else:
      return inventory

  #getCurrentInventory = 10.0
  def getCurrentInventory(self):
    """
      Returns current inventory
    """
    return self.getInventory(simulation_state=self.getPortalCurrentInventoryStateList(), ignore_variation=1)
    #return self.getInventory(at_date=DateTime(), ignore_variation=1)

  def getFutureInventory(self):
    """
      Returns current inventory
    """
    return self.getInventory(ignore_variation=1,
                             simulation_state=list(self.getPortalFutureInventoryStateList())+ \
                                              list(self.getPortalReservedInventoryStateList())+ \
                                              list(self.getPortalCurrentInventoryStateList()))

  def getAvailableInventory(self):
    """
      Returns current inventory
    """
    at_date=DateTime()
    current = self.getCurrentInventory()
    result = self.Resource_zGetInventory( resource_uid = [self.resource_uid], ignore_variation=1,
                                          omit_simulation = 1, omit_input = 1,
                                          section_category = self.getPortalDefaultSectionCategory(),
                                          simulation_state = self.getPortalReservedInventoryStateList())
    reserved_inventory = None
    if len(result) > 0:
      reserved_inventory = result[0].inventory
    if reserved_inventory is None:
      reserved_inventory = 0.0
    return current + reserved_inventory

  def getQuantityUnit(self, **kw):
    try:
      resource = self.portal_categories.unrestrictedTraverse(self.resource_relative_url)
      return resource.getQuantityUnit()
    except AttributeError:
      return ''


class InventoryListBrain(ZSQLBrain):
  """
    Lists each variation
  """

  # Stock management
  def getInventory(self, **kw):
    """
    Returns the inventory
    """
    simulation_tool = getToolByName(self,'portal_simulation')
    return simulation_tool.getInventory(node=self.node_relative_url,variation_text=self.variation_text,
                                 resource=self.resource_relative_url,**kw)

  #getCurrentInventory = 10.0
  def getCurrentInventory(self,**kw):
    """
      Returns current inventory
    """
    simulation_tool = getToolByName(self,'portal_simulation')
    return simulation_tool.getCurrentInventory(node=self.node_relative_url,variation_text=self.variation_text,
                                 resource=self.resource_relative_url,**kw)

  def getFutureInventory(self,**kw):
    """
      Returns current inventory
    """
    simulation_tool = getToolByName(self,'portal_simulation')
    return simulation_tool.getFutureInventory(node=self.node_relative_url,variation_text=self.variation_text,
                                 resource=self.resource_relative_url,**kw)

  def getAvailableInventory(self,**kw):
    """
      Returns current inventory
    """
    simulation_tool = getToolByName(self,'portal_simulation')
    return simulation_tool.getAvailableInventory(node=self.node_relative_url,variation_text=self.variation_text,
                                 resource=self.resource_relative_url,**kw)

  def getQuantity(self, **kw):
    result = self.Delivery_zGetTotal( resource_uid = [self.resource_uid],
                                      variation_text = self.variation_text)
    inventory = None
    if len(result) > 0:
      inventory = result[0].inventory
    if inventory is None:
      return 0.0
    else:
      return inventory

  def getQuantityUnit(self, **kw):
    try:
      resource = self.portal_categories.unrestrictedTraverse(self.resource_relative_url)
      return resource.getQuantityUnit()
    except AttributeError:
      return ''

  def getListItemUrl(self, cname_id, selection_index, selection_name):
    try:
      if cname_id in ('getExplanationText','getExplanation', ):
        o = self.getObject()
        if o is not None:
          explanation = o.getExplanationValue()
          if explanation is not None:
            return '%s/%s' % (self.portal_url.getPortalObject().absolute_url(), explanation.getRelativeUrl())
        else:
          return ''
      elif cname_id in ('getAggregateList','getAggregateListText',):
        kw = {
               'list_method_id' : 'Resource_zGetAggregateList',
               'explanation_uid' : self.explanation_uid,
               'node_uid' : self.node_uid,
               'section_uid' : self.section_uid,
               'variation_text' : self.variation_text,
               'resource_uid' : self.resource_uid,
               'reset': 1
             }
        url_params_string = make_query(kw)
        # should be search XXX
        return '%s/piece_tissu?%s ' % (
                        self.portal_url.getPortalObject().absolute_url(),
                        url_params_string
                        )
      elif cname_id in ('getCurrentInventory',):
          resource = self.portal_categories.unrestrictedTraverse(self.resource_relative_url)
          return '%s/Resource_movementHistoryView?%s&reset=1' % (resource.absolute_url(),
          make_query(variation_text=self.variation_text, selection_name=selection_name, selection_index=selection_index,
                     simulation_state=list(self.getPortalCurrentInventoryStateList())))
      elif cname_id in ('getAvailableInventory',):
          resource = self.portal_categories.unrestrictedTraverse(self.resource_relative_url)
          return '%s/Resource_movementHistoryView?%s&reset=1' % (resource.absolute_url(),
            make_query(variation_text=self.variation_text, selection_name=selection_name, selection_index=selection_index,omit_simulation = 1, omit_input = 1,
            simulation_state=list(self.getPortalReservedInventoryStateList())))
      elif cname_id in ('getFutureInventory','inventory', ):
          resource = self.portal_categories.unrestrictedTraverse(self.resource_relative_url)
          return '%s/Resource_movementHistoryView?%s&reset=1' % (resource.absolute_url(),
             make_query(variation_text=self.variation_text,
             selection_name=selection_name, selection_index=selection_index, simulation_state=list(self.getPortalFutureInventoryStateList())+list(self.getPortalReservedInventoryStateList())))
      elif cname_id in ('getInventoryAtDate',):
          resource = self.portal_categories.unrestrictedTraverse(self.resource_relative_url)
          return '%s/Resource_movementHistoryView?%s&reset=1' % (resource.absolute_url(),
                 make_query(variation_text=self.variation_text, to_date=self.at_date,
                 selection_name=selection_name, selection_index=selection_index, simulation_state=list(self.getPortalFutureInventoryStateList())+list(self.getPortalReservedInventoryStateList())))
      else:
        resource = self.portal_categories.unrestrictedTraverse(self.resource_relative_url)
        return '%s/Resource_movementHistoryView?%s&reset=1' % (resource.absolute_url(),
          make_query(variation_text=self.variation_text, selection_name=selection_name, selection_index=selection_index))
    except (AttributeError, KeyError):
      return ''

  def getAggregateListText(self):
    aggregate_list = self.Resource_zGetAggregateList(
                                   explanation_uid = self.explanation_uid,
                                   node_uid = self.node_uid,
                                   section_uid = self.section_uid,
                                   variation_text = self.variation_text,
                                   resource_uid = self.resource_uid)
    result = []
    for o in aggregate_list:
      result.append(o.relative_url)
    return '<br>'.join(result)

  def getExplanationText(self):
    # Returns an explanation of the movement
    o = self.getObject()
    if o is not None:
      portal_type = o.getPortalType()
      if portal_type == "Simulation Movement":
        order = o.getExplanationValue()
        if order is not None:
          if order.getPortalType() == 'Sales Order' :
            return "%s %s %s" % ('Commande vente', order.getId(), order.getDestinationDecisionOrganisationTitle())
          elif order.getPortalType() == 'Purchase Order' :
            return "%s %s %s" % ('Commande achat', order.getId(), order.getSourceDecisionTitle())
          elif order.getPortalType() == 'Production Order' :
            return "%s %s %s %ip" % ('OF', order.getId(), order.getDescription(), order.getTotalQuantity())
          else :
            return "%s %s" % ('Simulated Order', order.getId()) # Tried to use unicode but failed - ListBot must use unicode in % replacements
      else:
        LOG("Delivery Value",0,str(self.path))
        delivery = o.getExplanationValue()
        LOG("Delivery Value",0,str(delivery))
        if delivery is not None:
          causality = delivery.getCausalityValue()
          if causality is None:
            if delivery.getPortalType() == 'Sales Packing List' :
              return "%s %s %s" % ('Livraison vente', delivery.getId(), delivery.getDestinationDecisionOrganisationTitle())
            elif delivery.getPortalType() == 'Purchase Packing List' :
              return "%s %s %s" % ('Livraison achat', delivery.getId(), delivery.getSourceDecisionTitle())
            else :
              return "%s %s" % (delivery.getPortalType(), delivery.getId())
          else:
            if delivery.getPortalType() == 'Sales Packing List' :
              return "%s %s %s (cde %s)" % ('Livraison vente', delivery.getId(), delivery.getDestinationDecisionOrganisationTitle(), causality.getId())
            elif delivery.getPortalType() == 'Purchase Packing List' :
              return "%s %s %s (cde %s)" % ('Livraison achat', delivery.getId(), delivery.getSourceDecisionTitle(), causality.getId())
            elif delivery.getPortalType() == 'Production Packing List' :
              return "%s %s (of %s %s %ip)" % ('Livraison fabrication', delivery.getId(), causality.getId(), causality.getDescription(), causality.getTotalQuantity())
            elif delivery.getPortalType() == 'Production Report' :
              return "%s %s (of %s %s %ip)" % ('Rapport fabrication', delivery.getId(), causality.getId(), causality.getDescription(), causality.getTotalQuantity())
            else :
              return "%s %s (%s %s)" % (delivery.getPortalType(), delivery.getId(),
                              causality.getPortalType(), causality.getId())
    return "Unknown"

class DeliveryListBrain(InventoryListBrain):
  """
    Lists each variation
  """

  # Stock management
  def getInventory(self, at_date = None, ignore_variation=0, simulation_state=None, **kw):
    if type(simulation_state) is type('a'):
      simulation_state = [simulation_state]
    if hasattr(self, 'where_expression'):
      where_expression = self.where_expression
    else:
      where_expression = None
    result = self.Resource_zGetInventory( resource_uid = [self.resource_uid],
                                          to_date=at_date,
                                          section_category = self.getPortalDefaultSectionCategory(),
                                          variation_text = self.variation_text,
                                          simulation_state = simulation_state,
                                          where_expression = where_expression)
    inventory = None
    if len(result) > 0:
      inventory = result[0].inventory
    if inventory is None:
      return 0.0
    else:
      return inventory

  def getAvailableInventory(self):
    """
      Returns current inventory at current date
    """
    at_date=DateTime()
    current = self.getCurrentInventory()
    result = self.Resource_zGetInventory( resource_uid = [self.resource_uid],
                                          omit_simulation = 1, omit_input = 1,
                                          section_category = self.getPortalDefaultSectionCategory(),
                                          variation_text = self.variation_text,
                                          simulation_state = self.getPortalReservedInventoryStateList())
    reserved_inventory = None
    if len(result) > 0:
      reserved_inventory = result[0].inventory
    if reserved_inventory is None:
      reserved_inventory = 0.0
    return current + reserved_inventory

  def getInventoryAtDate(self):
    """
      Returns inventory at the date provided by the SQL method
    """
    at_date=self.at_date
    LOG("At Date",0,str(at_date))
    return self.getInventory(at_date=at_date, ignore_variation=0, simulation_state=list(self.getPortalFutureInventoryStateList())+list(self.getPortalReservedInventoryStateList())+list(self.getPortalCurrentInventoryStateList()))

