#-------------------------------------------------------------------------------
# Name:         WEAPOPT
# Purpose:      Extract network topology from a WEAP model
# Author:       David Rheinheimer
#-------------------------------------------------------------------------------

# Import system modules
import csv, shutil, odbc, os, sys, time, datetime
from time import sleep
import numpy as np
from collections import OrderedDict
from win32com.client import Dispatch

# creates the paradox DSN
# could be extended to create a DSN for any database flavor
def makeDSN(dbDir):
    dsn = """
    Driver={{Microsoft Paradox Driver (*.db )}};
    DriverID=538;Fil=Paradox 5.X;
    DefaultDir={0};Dbq={0};
    CollatingSequence=ASCII;
    """.format(dbDir)
    return dsn

    # connect to the WEAP area databases
def queryDb(dbname):
    conn = None
    cursor = None
    dsn = makeDSN(modeldir)
    conn = odbc.odbc(dsn)    
    cursor = conn.cursor()
    sql = 'SELECT * FROM {0};'.format(dbname)
    cursor.execute(sql)
    items = cursor.fetchall()
    cursor.close()
    conn = None
    return items

def connectDb(dbpath):
    conn = Dispatch("ADODB.Connection")
    p = 'Microsoft.Jet.OLEDB.4.0'
    c = 'Data Source={};Extended Properties=Paradox 5.x;'
    conn.Provider = p
    conn.ConnectionString = c.format(dbpath)
    return conn

    # connect to the WEAP area databases
def queryDbSQL(dbdir,SQLstr):
    conn = odbc.odbc(makeDSN(dbdir))
    cursor = conn.cursor()
    cursor.execute(SQLstr)
    items = cursor.fetchall()
    cursor.close()
    conn = None
    return items

# return a dict of the model objects
def getObjects():
    objdict = OrderedDict()
    objects = queryDb('Objects')
    for obj in objects:
        objdef = list(obj[1:])
        objdef[0] = str(objdef[0]) # change the object name to a normal string
        objdict[str(obj[0])] = objdef
    return objdict

def realNode(nodename):
    return nodename.split('-')[0]

def getFeatures():

    # get the arcs & nodes
    arcs = queryDb('Arcs')
    links = OrderedDict()
    nodes = []
    arcarray = []
    for arc in arcs:
        l = str(arc[0])
        n1 = str(arc[2])
        n2 = str(arc[3])
        if n1=='1' or n1=='2':
            n1='1-'+l # replace node 1 with something more specific
        if n2=='1' or n2=='2':
            n2='1-'+l # likewise...
        links[l] = [n1,n2]

        # add to nodes
        for n in [n1,n2]:
            if nodes.count(n)==0: nodes.append(n)

    return nodes, links

def makeNodeDict():
    nodedict = {}
    for node in nodes:
        if node.count('-')>0:
            reachname = objdict[node.split('-')[1]][0]
            if reachname.count('Headflow') > 0:
                nodename = reachname.replace('Below ','')
            else:
                nodename = 'Outflow '+reachname
        else:
            nodename = objdict[realNode(node)][0]
        nodedict[node] = nodename
    return nodedict

def makeLinkDicts():
    linkdictnum = OrderedDict()
    linkdictstr = OrderedDict()
    riverdict = OrderedDict()
    
    for l in links.keys():
        
        LinkName = objdict[l][0]       
        n0, n1 = links[l]
        name0, name1 = nodedict[n0], nodedict[n1]        
        
        ObjType = objdict[l][4]
        if ObjType==7:  # transmission links
            ReachName = RiverName = LinkName
        elif ObjType==8: # return flows
            ReachName = RiverName = "Return Flow from {0} to {1}".format(name0, name1)
        else:    
            RiverID = str(objdict[l][5])
            RiverName = objdict[RiverID][0] 
            ReachName = '{0} from {1} to {2}'.format(RiverName, name0, name1)
        
        linkdictnum[l] = ReachName
        linkdictstr[str(links[l])] = ReachName
        riverdict[tuple(links[l])] = RiverName

    return linkdictnum, linkdictstr, riverdict

def getSelectNodes(objtype):

    # connect to the WEAP area databases
    conn = odbc.odbc(makeDSN(modeldir))
    cursor = conn.cursor()

    # get the arcs
    cursor.execute('SELECT * FROM Objects WHERE TypeID={0};'.format(str(objtype)))
    objects = cursor.fetchall()
    cursor.close()
    conn = None
    nodes = []
    for obj in objects:
        nodes.append(str(obj[0]))
    return nodes

# return a subset of the links
# generaltypeseek = general input link type, e.g. 16 = river reach
# specifictypeseek = specific link class, e.g. 15 = diversion; 6 = river
def getSelectLinks(searchtype):

    # get the objects
    objdict = getObjects()

    getLinksDirectly = [7,8]
    
    selectlinks = []
    for link in links.keys():
    
        if searchtype in getLinksDirectly: # transmission links are not part of a larger link
            specificobj = link
        else: # all other links are a part of another link
            specificobj = str(objdict[link][5])
        if specificobj == '0': continue
        specifictype = objdict[specificobj][4]
        if specifictype == searchtype:
            selectlinks.append(links[link])
    return selectlinks

# return the headflow reaches
# generaltypeseek = general input link type, e.g. 16 = river reach
# specifictypeseek = specific link class, e.g. 15 = diversion; 6 = river
def getHeadflowNodesLinks():

    # connect to the WEAP area databases
    objects = queryDb('Objects')
    objlist = []
    for obj in objects: objlist.append(str(obj[0]))

    headflownodes = []
    for link in links.values():
        upnode = link[0]
        realupnode = realNode(upnode)
        if realupnode=='1' or realupnode=='2':
            headflownodes.append(upnode)

    headflowlinks = []
    for link in links.keys():
        loc = objlist.index(link)
        NodeAbove = str(objects[loc][14])
        if not NodeAbove=='None':
            NodeAboveLoc = objlist.index(NodeAbove)
            NodeAboveType = str(objects[NodeAboveLoc][5])
            if NodeAboveType == '6': headflowlinks.append(links[link])

    return headflownodes, headflowlinks

def getOutflowNodesLinks():

    # connect to the WEAP area databases
    objects = queryDb('Objects')
    objlist = []
    for obj in objects: objlist.append(str(obj[0]))

    outflownodes = []
    outflowlinks = []
    for link in links.values():
        downnode = link[1]
        realdownnode = realNode(downnode)
        if realdownnode=='1' or realdownnode=='2':
            outflownodes.append(downnode)
            outflowlinks.append(link)

    return outflownodes, outflowlinks

## create the connectivity matrix from WEAP model Arcs.db
#def makeC(nodes,links):

    #ncnt = len(nodes)
    #C = zeros((ncnt,ncnt))

    #for link in links.values():
        #i1 = nodes.index(link[0])
        #i2 = nodes.index(link[1])
        #C[i1,i2] = int(1)
    #C = C.tolist()
    #C.insert(0,['']+nodes)
    #for i,n in enumerate(nodes):
        #C[i+1].insert(0,n)
    #idx = range(ncnt)
    #for i,j in [(i,j) for i in idx for j in idx]:
        #C[i+1][j+1] = int(C[i+1][j+1])
    #return C

def copyfile(templatedir,fname,newname=None):
    if newname == None:
        newname = fname
    src = os.path.join(templatedir, fname)
    dest = os.path.join(outdir, newname)
    shutil.copyfile(src, dest)

def makeFile(fname):
    f = open(os.path.join(outdir, fname), 'wb')
    f.close()

def writeAppend(fname, lines):
    f = open(os.path.join(outdir, fname), 'a')
    if type(lines)!=list:
        lines = [lines]
    for line in lines:
        f.writelines(line + '\n')
    f.close()

def getColWidths(datatable):

    try:
        if len(datatable) == np.size(datatable):
            w = 0
            for d in datatable:
                w = max(w, len(d)+1)
            return w
    except:
        pass
    w = []
    for r,datarow in enumerate(datatable):
        for i,d in enumerate(datarow):
            if type(d)==list:
                if r==0:
                    w.append([])
                for j,subd in enumerate(d):
                    if r==0: w[i].append(0)
                    w[i][j] = max(w[i][j], len(str(subd))+1)
            else:
                if r==0:
                    w.append(0)
                if i==0:
                    w[i] = max(w[i], len(str(d))+2)
                else:
                    w[i] = max(w[i], len(str(d))+2)
    return w

# make a list of lines to add to an include file
def makeIncludeSet(fname, sname, sdesc, sdata, sdict=None):

    if not sdata:
        return

    # make the first line
    lines = ['set {} "{}"'.format(sname,sdesc)]

    lines.append('/')
    w = getColWidths(sdata)

    # add single-value data (e.g., nodes)
    if np.size(sdata)==np.shape(sdata)[0]:
        for i,name in enumerate(sdata):
            line = (str(name)).ljust(w)
            if sdict:
                line += '"%s"' % sdict[name]
            lines.append(line)

    # add multiple-value data (e.g., links)
    else:
        for i,row in enumerate(sdata):
            line = ''
            for j, name in enumerate(row):
                if j > 0: line += '.'
                line += (str(name)).ljust(w[j])
            if sdict:
                line += '"%s"' % sdict[str(row)]
            lines.append(line)

        # update the list of lines to be returned


    lines.append('/ ;\n')

    writeAppend(fname, lines)

# makes an include file from a set of lines
# useAltInRows use used to indicate whether the initial row identies should use an alternative name
# This is useful since sometimes rows represent dates, when we don't want to accidentally overwrite the date.
# Use 'True' for the connectivity matrix.
def makeIncludeTable(fname, tname, tdesc, tdata, rdim, cdim):

    # make the first lines
    lines = ['table {} "{}"'.format(tname, tdesc)]

    w = getColWidths(tdata)
    # add the data

    #useAlt = True
    for r,row in enumerate(tdata):
            
        line = ''
        for c,col in enumerate(row):
            if (c > 0 and c < rdim and r >= cdim) or (c >= rdim and r > 0 and r < cdim):
                prefix = '.'
            else:
                prefix = ''
            featurename = str(tdata[r][c])
            line += (prefix + featurename).ljust(w[c])
        lines.append(line)
    lines.append(';\n')

    writeInclude(fname, lines)

def getObjectCodes(names,dictionary):

    codes = []
    for n in names:
        for key,value in dictionary.iteritems():
            if value==n: codes.append(key)

    return codes

def printErrorMessage(problemchildname):
    print('WARNING: Could not process "%s". See other warnings.' % problemchildname)
    
############################################
############################################
############################################

def makeGAMSmodel(debug=1):
    
    global areasdir, modeldir, outdir
    global nodes, links
    global linkdict, objdict, nodedict, nodedict_reverse
    global linkdictnum, linkdictstr, ldict
    
    model = 'CEC_Yuba_Ops'
    
    curpath = str(sys.path[0])
    os.chdir(curpath)
    areasdir = os.path.abspath(os.path.expanduser('~/Documents/WEAP Areas'))
  
    modeldir = os.path.abspath(os.pardir)
    outdir = os.path.join(curpath, 'WEAPOPT')
    
    # create the 'optimization' model folder if it doesn't already exist
    #if os.path.exists(outdir):
    #    shutil.rmtree(outdir)
    #    sleep(1)
    
    #os.mkdir(outdir)

    # copy all files from model file folder
    #supportdir = os.path.join(curpath, 'model_files')
    #for fname in os.listdir(supportdir):
    #    copyfile(supportdir, fname)

    # make empty files
    makeFile('nodes.inc')
    makeFile('links.inc')

    # ======================
    # Set up model structure
    # ======================

    print ('setting up model structure')

    # get all the nodes and links
    nodes, links = getFeatures()
    objdict = getObjects()
    
    if debug:
        f = open('objects.csv', 'wb')
        writer = csv.writer(f)
        for obj in objdict.keys():
            writer.writerow([obj] + objdict[obj])
        f.close()
        
    # make a node dictionary (to look up a node's name given the node)
    nodedict = makeNodeDict()
    
    # make a reverse node dictionary (to look up a node's ID given it's name)
    nodedict_reverse = {}
    for node in nodedict.keys():
        nodename = nodedict[node]
        nodedict_reverse[nodename] = node

    # make a link dictionary
    linkdictnum, linkdictstr, ldict = makeLinkDicts()

    # get specific model features
    HFnodes, HFlinks = getHeadflowNodesLinks()
    OFnodes, OFlinks = getOutflowNodesLinks()
    Hab = getSelectLinks(6)
    Res = getSelectNodes(4)
    Sp = [link for link in links.values() if link[0] in Res and link in Hab]
    IFR = getSelectNodes(9)
    Ph = getSelectNodes(14)
    Dem = getSelectNodes(1)
    Div = getSelectLinks(15)
    TL = getSelectLinks(7)
    RF = getSelectLinks(8)

    # make the node & link sets
    makeIncludeSet('nodes.inc','n','all the nodes', nodes, sdict=nodedict)
    writeAppend('nodes.inc','alias (n,n1,n2) ;')
    makeIncludeSet('links.inc','l(n,n)','all the links', links.values(),sdict=linkdictstr)
    
    # =========================================================================
    # write a node name-to-ID dictionary to CSV for later use in WEAP
    # this is used in WEAP/VBScript
    f = open(r'nodedict.csv', 'wb')
    names = [nodedict[n] for n in nodes]
    names.sort()
    writelist = [[name, nodedict_reverse[name]] for name in names]
    csv.writer(f).writerows(writelist)
    f.close()
    
    # write a river name-to-ID dictionary to CSV for later use in WEAP
    # note: this is a one-to-many mapping, so multiple river name listings are possible
     #= LinkNameDict(links, objdict)
    links2 = ldict.keys()
    links2.sort()    
    names = ldict.values()
    names.sort()
    outlist = []
    for name in names:
        for l2 in links2[:]:
            if ldict[l2] == name:
                outlist.append([l2[0], l2[1], name])
                links2.remove(l2)
    f = open(r'linkdict.csv', 'wb')
    csv.writer(f).writerows(outlist)
    f.close()

    # update the include files with subsets
    makeIncludeSet('nodes.inc','hf(n)','headflow nodes',HFnodes,sdict=nodedict)
    makeIncludeSet('nodes.inc','out(n)', 'outflow nodes', OFnodes,sdict=nodedict)
    makeIncludeSet('links.inc','hab(n,n)','natural reaches',Hab,sdict=linkdictstr)
    makeIncludeSet('nodes.inc','res(n)','reservoirs',Res,sdict=nodedict)       
    makeIncludeSet('links.inc','sp(n,n)','spill (reaches below reservoirs)',Sp,sdict=linkdictstr)
    makeIncludeSet('nodes.inc','ifr(n)','minimum instream flow requirement locations',IFR,sdict=nodedict)            
    makeIncludeSet('nodes.inc','ph(n)','powerhouses',Ph,sdict=nodedict)
    makeIncludeSet('links.inc','ch(n,n)','artificial channels',Div,sdict=linkdictstr)
    makeIncludeSet('links.inc','tl(n,n)','transmission links',TL,sdict=linkdictstr)
    makeIncludeSet('links.inc','rf(n,n)','return flow links',RF,sdict=linkdictstr)
    makeIncludeSet('nodes.inc','dem(n)','water supply demand sites',Dem, sdict=nodedict)

    # this ensures that WEAPOPTtools will compile every time
    for f in os.listdir('.'):
        if f[-3:]=='pyc':
            os.remove(f)
    
    print('finished')
    
if __name__ == '__main__':
    makeGAMSmodel(debug=0)
    