# import
import pandas as pd
from os.path import join
import xml.etree.ElementTree as ET
import os
import zipfile
from pypxlib import Table
from collections import OrderedDict
import shutil

'''
a shortcut to ET.SubElenment(parent, child).text ( and *.text = text )
'''
def add_node(parent, child, text):
    if type(text)==str:
        ET.SubElement(parent, child).text = text
    else:
        ET.SubElement(parent, child)
        
# add resource attribute
def add_attribute(resources, resource_name, attr_dict):
    for resource in resources:
        if resource.find('name').text == resource_name:
            attr = ET.SubElement(resource, 'attribute')
            for attr_name, attr_text in attr_dict.items():
                add_node(attr, attr_name, attr_text)
        
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

def create_xml_template(tpl_name):

    # load features and variables from csv
    features_all = pd.read_csv('./WEAP_default_features.csv')
    variables_all = pd.read_csv('./WEAP_default_variables.csv')
    
    var_features = variables_all.feature.unique()
    cat_features = features_all.feature.unique()
    
    # template name
    
    tpl = ET.Element('template_definition')
    #tree = ET.ElementTree(tpl)
    ET.SubElement(tpl, 'template_name').text = tpl_name
    
    # define link lines
    width = 4
    linkstyle = {}
    linkstyle['river'] = ['solid', 'blue', width]
    linkstyle['diversion'] = ['solid', 'orange', width]
    linkstyle['transmission_link'] = ['solid', 'green', width]
    linkstyle['return_flow'] = ['solid', 'red', width]
    linkstyle['runoff_infiltration'] = ['dashed', 'blue', width]
    
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
                pass
            
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
    #for feature in var_features:
    for f in features_all.itertuples():
        
        if f.feature=='catchment':
            pass
        
        if f.feature not in cat_features:
            continue
        
        # get resource category
        category = features_all[features_all.feature==f.feature].category.iloc[0][:-1].upper()
    
        # add the resource subelement
        resource = ET.SubElement(resources, 'resource')
        
        # add resource layout info
        add_node(resource, 'type', category)
        add_node(resource, 'name', f.feature)
        layout = ET.SubElement(resource, 'layout')
        item = ET.SubElement(layout, 'item')
        add_node(item, 'name', 'image')
        add_node(item, 'value', 'images\\'+f.feature+'.png')
        
        if category == 'LINK':
            for i, iname in enumerate(['symbol','colour','line_weight']):
                item = ET.SubElement(layout, 'item')
                add_node(item, 'name', iname)
                add_node(item, 'value', str(linkstyle[f.feature][i]))
        
        item = ET.SubElement(layout, 'item')
        add_node(item, 'name', 'group')
        add_node(item, 'value', f.feature)
        
        # add variables
        feature_variables = variables_all[variables_all.feature == f.feature]
        for v in feature_variables.itertuples():
            
            if v.variable_type=='Water Quality':
                continue
            
            attr = ET.SubElement(resource, 'attribute')
            add_node(attr, 'name', v.variable_name.replace(' ', '_'))
            add_node(attr, 'dimension', v.dimension)
            add_node(attr, 'unit', v.hydra_unit)
            add_node(attr, 'is_var', 'N')
            add_node(attr, 'data_type', 'descriptor')
            
        # add basic result variables - inflow/outflow
        for v in ['inflow','outflow']:
            attr = ET.SubElement(resource, 'attribute')
            add_node(attr, 'name', v)
            add_node(attr, 'dimension', 'Volume')
            add_node(attr, 'unit', '1e6 m^3')
            add_node(attr, 'is_var', 'Y')
            add_node(attr, 'data_type', 'timeseries')        
            
    return tpl#, tree

def make_type_dict(weapdir):
    typedefs = Table(join(weapdir, '_Dictionary', 'NodeTypes.DB'))
    type_dict = {}
    for t in typedefs:
        type_dict[t.TypeID] = str(t.Name.lower()).replace(' ','_').replace('/','_')
    return type_dict

'''
convert paradox db to pandas df
'''
def px_to_df(pxdb):
    with Table(pxdb) as units:
        fields = list(units.fields)
        rows = [(row[fields[0]], [row[field] for field in fields[1:]]) for row in units]
        df = pd.DataFrame.from_items(rows, orient='index', columns=fields[1:])
    return df    
    
def add_custom_variables(tpl, weapdir, area):

    areadir = join(weapdir, area)
    
    # lookup dataframes for...
    
    # type:
    type_df = px_to_df(pxdb = join(weapdir, '_Dictionary', 'NodeTypes.DB'))
    
    # catagory:
    category_df = px_to_df(pxdb = join(weapdir, '_Dictionary', 'Category.DB'))
    
    # units:
    units_df = px_to_df(pxdb = join(areadir, 'Units.DB'))
    
    # weap-hydra units
    weap_hydra_units_df = pd.read_csv('weap_hydra_units.csv', index_col=0)
    
    resources = tpl.find('resources')
    
    # read user variables database
    with Table(file_path=join(areadir, 'UserVariables.db')) as uservariables:
    
        # loop through all user variables and add them to the template
        for v in uservariables:
            
            attr_dict = {}
            
            # feature name
            if v.TypeID:
                resource_name = str(type_df.loc[v.TypeID].Name).lower().replace(' ','_').replace('/', '_')
            else:
                category = category_df.loc[v.CategoryID].Name
                if category == 'Treatment': resource_name = 'Wastewater_Treatment_Plant'
                elif category == 'Water Use': resource_name = 'Demand_Site'
                # need to add more categories if needed, perhaps from lookup table
            
            # determine units
            weap_unit_name = units_df.loc[-v.NumUnitFieldID].Name
            hydra_unit_abbr = weap_hydra_units_df.loc[weap_unit_name].Hydra_abbr
            
            # data type
            if v.IsInteger:
                v_data_type = 'scalar'
            else:
                v_data_type = 'timeseries'
            
            # write the variable info to a dictionary
            attr_dict = OrderedDict()
            attr_dict['name'] = str(v.DisplayLabel).replace(' ','_')
            #attr_dict['description'] = v.GridComment
            attr_dict['dimension'] = 'Volume'
            attr_dict['unit'] = hydra_unit_abbr
            attr_dict['is_var'] = 'Y'
            attr_dict['data_type'] = v_data_type
            
            # write the variables to template, under resources
            add_attribute(resources, resource_name, attr_dict)
    
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

def main(tpl_name, custom_area, weapdir, write_template=True, direct_import=True, outdir=None):
    
    # check if input requirements are met
    if write_template and outdir==None:
        return
    
    # create template xml
    tpl = create_xml_template(tpl_name)

    # update template from specific model
    if custom_area:
        add_custom_variables(tpl, weapdir, custom_area)
    
    # create tree
    tree = ET.ElementTree(tpl)
    
    ## 1. write template to xml file and create hydra-friendly zip file
    if write_template:
        
        # remove old template directory
        tpl_path = join(outdir, tpl_name)
        if os.path.exists(tpl_path):
            shutil.rmtree(tpl_path)
            
        # create new template directory
        os.mkdir(tpl_path)
        shutil.copytree(src='template', dst=join(tpl_path, 'template'))
    
        # write template xml to file
        write_template_xml(tpl, tree, tpl_name)
        
        # create template zipfile for import to Hydra
        create_template_zipfile(tpl_name)
        
    ## 2. import xml directly
    
    
if __name__ == '__main__':

    weapdir = r'C:\Users\L03060467\Documents\WEAP Areas'
    #custom_area = 'Weaping River Basin'
    custom_area = None
    if custom_area:
        tpl_name = custom_area
    else:
        tpl_name = 'WEAP'
    outdir = '.'
    write_template = True
    direct_import = False
    
    main(tpl_name, custom_area, weapdir=weapdir, write_template=True, direct_import=False, outdir=outdir)

    print('finished')