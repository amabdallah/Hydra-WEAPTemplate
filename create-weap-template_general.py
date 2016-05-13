# import
import pandas as pd
from os.path import join
import xml.etree.ElementTree as ET
import os
import zipfile

'''
a shortcut to ET.SubElenment(parent, child).text ( and *.text = text )
'''
def add_node(parent, child, text):
    if type(text)==str:
        ET.SubElement(parent, child).text = text
    else:
        ET.SubElement(parent, child)
        
'''
pretty print xml from http://effbot.org/zone/element-lib.htm#prettyprint
'''
def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

'''
zip a directory - pilfered from the internet
'''
def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

def create_template_xml(tpl_name):

    # load features and variables from csv
    features_all = pd.read_csv('./WEAP_default_features.csv')
    variables_all = pd.read_csv('./WEAP_default_variables.csv')
    
    var_features = variables_all.feature.unique()
    cat_features = features_all.feature.unique()
    
    # template name
    
    tpl = ET.Element('template_definition')
    tree = ET.ElementTree(tpl)
    ET.SubElement(tpl, 'template_name').text = tpl_name
    
    # define link lines
    linkstyle = {}
    linkstyle['river'] = ['solid','blue',2]
    linkstyle['diversion'] = ['solid','orange',2]
    linkstyle['transmission_link'] = ['solid','green',2]
    linkstyle['return_flow'] = ['solid','red',2]
    
    # add layout
    
    layout = ET.SubElement(tpl, 'layout')
    item = ET.SubElement(layout, 'item')
    add_node(item, 'name', 'grouping')
    value = ET.SubElement(item, 'value')
    add_node(value, 'name', tpl_name)
    add_node(value, 'description', tpl_name)
    categories = ET.SubElement(value, 'categories')
    
    cats = features_all.category.unique()
    for cat in cats:
        category = ET.SubElement(categories, 'category')
        for attr in ['name', 'description', 'displayname']:
            add_node(category, attr, cat)
        groups = ET.SubElement(category, 'groups')
        
        features = features_all[features_all.category==cat]
        for f in features.itertuples():
            
            if f.feature not in var_features:
                continue
            
            group = ET.SubElement(groups, 'group')
            add_node(group, 'name', f.feature)
            add_node(group, 'description', f.description)
            add_node(group, 'displayname', f.displayname)
            add_node(group, 'image', 'images\\%s.png' % f.feature)
    
    
    # add resources
    
    resources = ET.SubElement(tpl, 'resources')
    
    # add a blank NETWORK resource if no NETWORK variables exist
    if 'NETWORK' not in categories:
        resource = ET.SubElement(resources, 'resource')
        add_node(resource, 'type', 'NETWORK')
        add_node(resource, 'name', 'key_assumptions')
    
    # add features and variables
    for feature in var_features:
        
        if feature not in cat_features:
            continue
        
        # get resource category
        category = features_all[features_all.feature==feature].category.iloc[0][:-1].upper()
    
        # add the resource subelement
        resource = ET.SubElement(resources, 'resource')
        
        # add resource layout info
        add_node(resource, 'type', category)
        add_node(resource, 'name', feature)
        layout = ET.SubElement(resource, 'layout')
        item = ET.SubElement(layout, 'item')
        add_node(item, 'name', 'image')
        add_node(item, 'value', 'images\\'+feature+'.png')
        
        if category == 'LINK':
            for i, iname in enumerate(['symbol','colour','line_weight']):
                item = ET.SubElement(layout, 'item')
                add_node(item, 'name', iname)
                add_node(item, 'value', str(linkstyle[feature][i]))
        
        item = ET.SubElement(layout, 'item')
        add_node(item, 'name', 'group')
        add_node(item, 'value', feature)
        
        # add variables
        feature_variables = variables_all[variables_all.feature == feature]
        for v in feature_variables.itertuples():
            
            if v.variable_type=='Water Quality':
                continue
            
            attr = ET.SubElement(resource, 'attribute')
            add_node(attr, 'name', v.variable_name.replace(' ', '_'))
            add_node(attr, 'dimension', v.dimension)
            add_node(attr, 'unit', v.hydra_unit)
            add_node(attr, 'is_var', 'Y')
            add_node(attr, 'data_type', 'timeseries')
            
    return tpl, tree
            
def write_template_xml(tpl, tree, tpl_name):
    
    # prettify
    indent(tpl)
    
    # write to file
    fout = join(tpl_name, './template/template.xml')
    tree.write(fout)
    
def create_template_zipfile(tpl_name):
    # create the zipfile
    zipf = zipfile.ZipFile(tpl_name + '.zip', 'w', zipfile.ZIP_DEFLATED)
    zipd = tpl_name + '/template'
    zipdir(zipd, zipf)
    zipf.close()

def main():
    
    tpl_name = 'WEAP basic'
    
    # create template xml as elementtree tree
    tpl, tree = create_template_xml(tpl_name)
    
    # write template xml to file
    write_template_xml(tpl, tree, tpl_name)
    
    # create template zipfile for import to Hydra
    create_template_zipfile(tpl_name)    
    
if __name__ == '__main__':
    main()

