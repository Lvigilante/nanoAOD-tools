import ROOT
import math, os,re
import numpy as np
ROOT.PyConfig.IgnoreCommandLineOptions = True

from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection, Object
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
from PhysicsTools.NanoAODTools.postprocessing.tools import matchObjectCollection, matchObjectCollectionMultiple
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetSmearer import jetSmearer
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.JetReCalibrator import JetReCalibrator

class jetmetUncertaintiesProducer(Module):
    def __init__(self, era, globalTag, jesUncertainties = [ "Total" ], jer="Summer16_25nsV1", jetType = "AK4PFchs", redoJEC=False, doResiduals=True, noGroom=False, METBranchName='MET', unclEnThreshold=15):

        self.era = era
        self.redoJEC = redoJEC
        self.doResiduals = doResiduals
        self.noGroom = noGroom
        self.unclEnThreshold = unclEnThreshold
        #--------------------------------------------------------------------------------------------
        # CV: globalTag and jetType not yet used, as there is no consistent set of txt files for
        #     JES uncertainties and JER scale factors and uncertainties yet
        #--------------------------------------------------------------------------------------------

        self.jesUncertainties = jesUncertainties

        # smear jet pT to account for measured difference in JER between data and simulation.
        self.jerInputFileName = "%s_MC_PtResolution_"%jer + jetType + ".txt"
        self.jerUncertaintyInputFileName = "%s_MC_SF_"%jer + jetType + ".txt"
        self.jetSmearer = jetSmearer(globalTag, jetType, self.jerInputFileName, self.jerUncertaintyInputFileName)

        if "AK4" in jetType : 
            self.jetBranchName = "Jet"
            self.genJetBranchName = "GenJet"
            self.genSubJetBranchName = None
            self.doGroomed = False
            self.corrMET = True
        elif "AK8" in jetType :
            self.jetBranchName = "FatJet"
            self.subJetBranchName = "SubJet"
            self.genJetBranchName = "GenJetAK8"
            self.genSubJetBranchName = "SubGenJetAK8"
            if not self.noGroom:
                self.doGroomed = True
            else:
                self.doGroomed = False
            self.corrMET = False
        else:
            raise ValueError("ERROR: Invalid jet type = '%s'!" % jetType)
        self.metBranchName = METBranchName
        self.rhoBranchName = "fixedGridRhoFastjetAll"
        self.lenVar = "n" + self.jetBranchName
        # To do : change to real values
        self.jmsVals = [1.00, 0.99, 1.01]
        

        # read jet energy scale (JES) uncertainties
        # (downloaded from https://twiki.cern.ch/twiki/bin/view/CMS/JECDataMC )
        self.jesInputFilePath = os.environ['CMSSW_BASE'] + "/src/PhysicsTools/NanoAODTools/data/jme/"
        if len(jesUncertainties) == 1 and jesUncertainties[0] == "Total":
            if self.era == "2016":
                self.jesUncertaintyInputFileName = "%s_Uncertainty_"%globalTag + jetType + ".txt"
            elif self.era == "2017":
                self.jesUncertaintyInputFileName = "%s_Uncertainty_"%globalTag + jetType + ".txt"
            elif self.era == "2018":
                self.jesUncertaintyInputFileName = "%s_Uncertainty_"%globalTag + jetType + ".txt"
            else:
                raise ValueError("ERROR: Invalid era = '%s'!" % self.era)
        else:
            if self.era == "2016":
                self.jesUncertaintyInputFileName = "%s_UncertaintySources_"%globalTag + jetType + ".txt"
            elif self.era == "2017":
                self.jesUncertaintyInputFileName = "%s_UncertaintySources_"%globalTag + jetType + ".txt"
            elif self.era == "2018":
                self.jesUncertaintyInputFileName = "%s_UncertaintySources_"%globalTag + jetType + ".txt"
            else:
                raise ValueError("ERROR: Invalid era = '%s'!" % self.era)


        # read all uncertainty source names from the loaded file
        if jesUncertainties[0] == "All":
            with open(self.jesInputFilePath+self.jesUncertaintyInputFileName) as f:
                lines = f.read().split("\n")
                sources = filter(lambda x: x.startswith("[") and x.endswith("]"), lines)
                sources = map(lambda x: x[1:-1], sources)
                self.jesUncertainties = sources
            

	if self.redoJEC :
	    self.jetReCalibrator    = JetReCalibrator(globalTag, jetType , self.doResiduals, self.jesInputFilePath, calculateSeparateCorrections = False, calculateType1METCorrection  = False)
        self.jetReCalibratorL1  = JetReCalibrator(globalTag, jetType , False, self.jesInputFilePath, calculateSeparateCorrections = True, calculateType1METCorrection  = False, upToLevel=1)
	

        # define energy threshold below which jets are considered as "unclustered energy"
        # (cf. JetMETCorrections/Type1MET/python/correctionTermsPfMetType1Type2_cff.py )
        #self.unclEnThreshold = 15.

        # load libraries for accessing JES scale factors and uncertainties from txt files
        for library in [ "libCondFormatsJetMETObjects", "libPhysicsToolsNanoAODTools" ]:
            if library not in ROOT.gSystem.GetLibraries():
                print("Load Library '%s'" % library.replace("lib", ""))
                ROOT.gSystem.Load(library)

    def beginJob(self):

        print("Loading jet energy scale (JES) uncertainties from file '%s'" % os.path.join(self.jesInputFilePath, self.jesUncertaintyInputFileName))
        #self.jesUncertainty = ROOT.JetCorrectionUncertainty(os.path.join(self.jesInputFilePath, self.jesUncertaintyInputFileName))
    
        self.jesUncertainty = {} 
        # implementation didn't seem to work for factorized JEC, try again another way
        for jesUncertainty in self.jesUncertainties:
            jesUncertainty_label = jesUncertainty
            if self.era == "2016" and jesUncertainty == 'Total' and len(self.jesUncertainties) == 1:
                jesUncertainty_label = ''
            elif self.era == "2017" and jesUncertainty == 'Total' and len(self.jesUncertainties) == 1:
                jesUncertainty_label = ''
            elif self.era == "2018" and jesUncertainty == 'Total' and len(self.jesUncertainties) == 1:
                jesUncertainty_label = ''
            pars = ROOT.JetCorrectorParameters(os.path.join(self.jesInputFilePath, self.jesUncertaintyInputFileName),jesUncertainty_label)
            self.jesUncertainty[jesUncertainty] = ROOT.JetCorrectionUncertainty(pars)    

        self.jetSmearer.beginJob()

    def endJob(self):

        self.jetSmearer.endJob()

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        self.out = wrappedOutputTree
        self.out.branch("%s_pt_nom" % self.jetBranchName, "F", lenVar=self.lenVar)
        self.out.branch("%s_corr_JEC" % self.jetBranchName, "F", lenVar=self.lenVar)
        self.out.branch("%s_corr_JER" % self.jetBranchName, "F", lenVar=self.lenVar)
        self.out.branch("%s_mass_nom" % self.jetBranchName, "F", lenVar=self.lenVar)
        if self.doGroomed:
            self.out.branch("%s_msoftdrop_nom" % self.jetBranchName, "F", lenVar=self.lenVar)
            
        if self.corrMET:
            self.out.branch("%s_pt_nom" % self.metBranchName, "F")
            self.out.branch("%s_phi_nom" % self.metBranchName, "F")
        
        for shift in [ "Up", "Down" ]:
            self.out.branch("%s_pt_jer%s" % (self.jetBranchName, shift), "F", lenVar=self.lenVar)
            self.out.branch("%s_mass_jer%s" % (self.jetBranchName, shift), "F", lenVar=self.lenVar)
            self.out.branch("%s_mass_jmr%s" % (self.jetBranchName, shift), "F", lenVar=self.lenVar)
            self.out.branch("%s_mass_jms%s" % (self.jetBranchName, shift), "F", lenVar=self.lenVar)

            if self.doGroomed: 
                self.out.branch("%s_msoftdrop_jer%s" % (self.jetBranchName, shift), "F", lenVar=self.lenVar)
                self.out.branch("%s_msoftdrop_jmr%s" % (self.jetBranchName, shift), "F", lenVar=self.lenVar)
                self.out.branch("%s_msoftdrop_jms%s" % (self.jetBranchName, shift), "F", lenVar=self.lenVar)

            if self.corrMET :
                self.out.branch("%s_pt_jer%s" % (self.metBranchName, shift), "F")
                self.out.branch("%s_phi_jer%s" % (self.metBranchName, shift), "F")
            for jesUncertainty in self.jesUncertainties:
                self.out.branch("%s_pt_jes%s%s" % (self.jetBranchName, jesUncertainty, shift), "F", lenVar=self.lenVar)
                self.out.branch("%s_mass_jes%s%s" % (self.jetBranchName, jesUncertainty, shift), "F", lenVar=self.lenVar)
                if self.doGroomed:
                    self.out.branch("%s_msoftdrop_jes%s%s" % (self.jetBranchName, jesUncertainty, shift), "F", lenVar=self.lenVar)
                if self.corrMET :
                    self.out.branch("%s_pt_jes%s%s" % (self.metBranchName, jesUncertainty, shift), "F")
                    self.out.branch("%s_phi_jes%s%s" % (self.metBranchName, jesUncertainty, shift), "F")
            if self.corrMET :
                self.out.branch("%s_pt_unclustEn%s" % (self.metBranchName, shift), "F")
                self.out.branch("%s_phi_unclustEn%s" % (self.metBranchName, shift), "F")
                        
    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        pass
    
    def analyze(self, event):
        """process event, return True (go to next module) or False (fail, go to next event)"""
        jets = Collection(event, self.jetBranchName )
        muons = Collection(event, "Muon" )
        genJets = Collection(event, self.genJetBranchName )

        if self.doGroomed :
            subJets = Collection(event, self.subJetBranchName )
            genSubJets = Collection(event, self.genSubJetBranchName )
            genSubJetMatcher = matchObjectCollectionMultiple( genJets, genSubJets, dRmax=0.8 )
            

        jets_pt_nom = []
        jets_corr_JEC = []
        jets_corr_JER = []
        jets_pt_jerUp   = []
        jets_pt_jerDown = []
        jets_pt_jesUp   = {}
        jets_pt_jesDown = {}
        jets_mass_nom = []
        jets_mass_jerUp   = []
        jets_mass_jerDown = []
        jets_mass_jmrUp   = []
        jets_mass_jmrDown = []
        jets_mass_jesUp   = {}
        jets_mass_jesDown = {}
        jets_mass_jmsUp   = []
        jets_mass_jmsDown = []
        for jesUncertainty in self.jesUncertainties:
            jets_pt_jesUp[jesUncertainty]   = []
            jets_pt_jesDown[jesUncertainty] = []
            jets_mass_jesUp[jesUncertainty]   = []
            jets_mass_jesDown[jesUncertainty] = []

        if self.corrMET :
            met = Object(event, self.metBranchName)
            rawmet = Object(event, "RawMET")
            defmet  = Object(event, "MET")

            ( t1met_px,       t1met_py       ) = ( met.pt*math.cos(met.phi), met.pt*math.sin(met.phi) )
            ( def_met_px,     def_met_py     ) = ( defmet.pt*math.cos(defmet.phi),   defmet.pt*math.sin(defmet.phi) )
            ( met_px,         met_py         ) = ( rawmet.pt*math.cos(rawmet.phi), rawmet.pt*math.sin(rawmet.phi) )
            ( met_px_nom,     met_py_nom     ) = ( met_px, met_py )
            ( met_px_jerUp,   met_py_jerUp   ) = ( met_px, met_py )
            ( met_px_jerDown, met_py_jerDown ) = ( met_px, met_py )
            ( met_px_jesUp,   met_py_jesUp   ) = ( {}, {} )
            ( met_px_jesDown, met_py_jesDown ) = ( {}, {} )
            for jesUncertainty in self.jesUncertainties:
                met_px_jesUp[jesUncertainty]   = met_px
                met_py_jesUp[jesUncertainty]   = met_py
                met_px_jesDown[jesUncertainty] = met_px
                met_py_jesDown[jesUncertainty] = met_py

        if self.doGroomed:
            jets_msdcorr_nom = []
            jets_msdcorr_jerUp   = []
            jets_msdcorr_jerDown = []
            jets_msdcorr_jmrUp   = []
            jets_msdcorr_jmrDown = []
            jets_msdcorr_jesUp   = {}
            jets_msdcorr_jesDown = {}
            jets_msdcorr_jmsUp   = []
            jets_msdcorr_jmsDown = []
            for jesUncertainty in self.jesUncertainties:
                jets_msdcorr_jesUp[jesUncertainty]   = []
                jets_msdcorr_jesDown[jesUncertainty] = []

             
        delta_x_T1Jet, delta_y_T1Jet = 0, 0
        delta_x_rawJet, delta_y_rawJet = 0, 0

        rho = getattr(event, self.rhoBranchName)

        # match reconstructed jets to generator level ones
        # (needed to evaluate JER scale factors and uncertainties)
        pairs = matchObjectCollection(jets, genJets)
        
        for jet in jets:
            genJet = pairs[jet]
            if self.doGroomed :                
                genGroomedSubJets = genSubJetMatcher[genJet] if genJet != None else None
                genGroomedJet = genGroomedSubJets[0].p4() + genGroomedSubJets[1].p4() if genGroomedSubJets != None and len(genGroomedSubJets) >= 2 else None
                if jet.subJetIdx1 >= 0 and jet.subJetIdx2 >= 0 :
                    groomedP4 = subJets[ jet.subJetIdx1 ].p4() + subJets[ jet.subJetIdx2].p4()
                else :
                    groomedP4 = None
                
            # evaluate JER scale factors and uncertainties
            # (cf. https://twiki.cern.ch/twiki/bin/view/CMS/JetResolution and https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookJetEnergyResolution )
            ( jet_pt_jerNomVal, jet_pt_jerUpVal, jet_pt_jerDownVal ) = self.jetSmearer.getSmearValsPt(jet, genJet, rho)
	    
            jet_pt      = jet.pt
            jet_pt_orig = jet_pt
            rawFactor   = jet.rawFactor
            if hasattr(jet, "rawFactor"):
                jet_rawpt = jet.pt * (1 - jet.rawFactor)
            else:
                jet_rawpt = -1.0 * jet.pt #If factor not present factor will be saved as -1
            
            if self.redoJEC or True: # needs to run!
                jet_pt          = self.jetReCalibrator.correct(jet,rho)

                newjet = ROOT.TLorentzVector()
                newjet.SetPtEtaPhiM(jet_pt_orig*(1-jet.rawFactor), jet.eta, jet.phi, jet.mass )
                muon_pt = 0
                if jet.muonIdx1>-1:
                    newjet = newjet - muons[jet.muonIdx1].p4()
                    muon_pt += muons[jet.muonIdx1].pt
                if jet.muonIdx2>-1:
                    newjet = newjet - muons[jet.muonIdx2].p4()
                    muon_pt += muons[jet.muonIdx2].pt

                jet.pt = newjet.Pt()
                jet.rawFactor = 0
                jet_pt_noMuL1L2L3   = self.jetReCalibrator.correct(jet,rho)   if self.jetReCalibrator.correct(jet,rho) > self.unclEnThreshold else jet.pt # only correct the non-mu fraction of the jet if it's above 15 GeV, otherwise take the raw pt
                jet_pt_noMuL1       = self.jetReCalibratorL1.correct(jet,rho) if self.jetReCalibrator.correct(jet,rho) > self.unclEnThreshold else jet.pt # only correct the non-mu fraction of the jet if it's above 15 GeV, otherwise take the raw pt

                ## setting jet back to original values
                jet.pt          = jet_pt
                jet.rawFactor   = rawFactor

            jec = jet_pt/jet_rawpt
            jets_corr_JEC.append(jet_pt/jet_rawpt)
            jets_corr_JER.append(jet_pt_jerNomVal)
            
            jet_pt_nom      = jet_pt
            jet_pt_L1L2L3   = jet_pt_noMuL1L2L3 + muon_pt
            jet_pt_L1       = jet_pt_noMuL1     + muon_pt

            if self.metBranchName == 'METFixEE2017':
                # get the delta for removing L1L2L3-L1 corrected jets in the EE region from the default MET branch.
                # Right now this will only be correct if we reapply the same JECs,
                # because there's no way to extract the L1L2L3 and L1 corrections that were actually used as input to the stored type1 MET...
                if jet_pt_L1L2L3 > self.unclEnThreshold and 2.65<abs(jet.eta)<3.14 and jet_rawpt < 50:
                    delta_x_T1Jet  += (jet_pt_L1L2L3-jet_pt_L1) * math.cos(jet.phi) + jet_rawpt * math.cos(jet.phi)#jet_rawpt * math.cos(jet.phi)
                    delta_y_T1Jet  += (jet_pt_L1L2L3-jet_pt_L1) * math.sin(jet.phi) + jet_rawpt * math.sin(jet.phi)#jet_rawpt * math.sin(jet.phi)

                # get the delta for removing raw jets in the EE region from the raw MET
                #if jet.pt > self.unclEnThreshold and 2.65<abs(jet.eta)<3.14 and jet.pt < 50:
                if jet_pt_L1L2L3 > self.unclEnThreshold and 2.65<abs(jet.eta)<3.14 and jet_rawpt < 50:
                    delta_x_rawJet += jet_rawpt * math.cos(jet.phi)#jet_rawpt * math.cos(jet.phi)
                    delta_y_rawJet += jet_rawpt * math.sin(jet.phi)#jet_rawpt * math.sin(jet.phi)

            if jet_pt_nom < 0.0:
                jet_pt_nom *= -1.0
            jet_pt_jerUp         = jet_pt_jerUpVal  *jet_pt_L1L2L3
            jet_pt_jerDown       = jet_pt_jerDownVal*jet_pt_L1L2L3
            jets_pt_nom    .append(jet_pt_nom)
            jets_pt_jerUp  .append(jet_pt_jerUpVal*jet_pt)
            jets_pt_jerDown.append(jet_pt_jerDownVal*jet_pt)
            # evaluate JES uncertainties
            jet_pt_jesUp     = {}
            jet_pt_jesDown   = {}
            jet_pt_jesUpT1   = {}
            jet_pt_jesDownT1 = {}
            jet_mass_jesUp   = {}
            jet_mass_jesDown = {}
            jet_mass_jmsUp   = []
            jet_mass_jmsDown = []

            
            # Evaluate JMS and JMR scale factors and uncertainties
            jmsNomVal = self.jmsVals[0]
            jmsDownVal = self.jmsVals[1]
            jmsUpVal = self.jmsVals[2]
            ( jet_mass_jmrNomVal, jet_mass_jmrUpVal, jet_mass_jmrDownVal ) = self.jetSmearer.getSmearValsM(jet, genJet)
            jet_mass_nom           = jet_pt_jerNomVal*jet_mass_jmrNomVal*jmsNomVal*jet.mass
            if jet_mass_nom < 0.0:
                jet_mass_nom *= -1.0
            jets_mass_nom    .append(jet_mass_nom)
            jets_mass_jerUp  .append(jet_pt_jerUpVal  *jet_mass_jmrNomVal *jmsNomVal  *jet.mass)
            jets_mass_jerDown.append(jet_pt_jerDownVal*jet_mass_jmrNomVal *jmsNomVal  *jet.mass)
            jets_mass_jmrUp  .append(jet_pt_jerNomVal *jet_mass_jmrUpVal  *jmsNomVal  *jet.mass)
            jets_mass_jmrDown.append(jet_pt_jerNomVal *jet_mass_jmrDownVal*jmsNomVal  *jet.mass)
            jets_mass_jmsUp  .append(jet_pt_jerNomVal *jet_mass_jmrNomVal *jmsUpVal   *jet.mass)
            jets_mass_jmsDown.append(jet_pt_jerNomVal *jet_mass_jmrNomVal *jmsDownVal *jet.mass)


            if self.doGroomed :
                # to evaluate JES uncertainties
                jet_msdcorr_jmsUp   = []
                jet_msdcorr_jmsDown = []
                jet_msdcorr_jesUp   = {}
                jet_msdcorr_jesDown = {}
                
                ( jet_msdcorr_jmrNomVal, jet_msdcorr_jmrUpVal, jet_msdcorr_jmrDownVal ) = self.jetSmearer.getSmearValsM(groomedP4, genGroomedJet) if groomedP4 != None and genGroomedJet != None else (0.,0.,0.)
                jet_msdcorr_raw = groomedP4.M() if groomedP4 != None else 0.0
                if jet_msdcorr_raw < 0.0:
                    jet_msdcorr_raw *= -1.0
                jet_msdcorr_nom           = jet_pt_jerNomVal*jet_msdcorr_jmrNomVal*jet_msdcorr_raw
                jets_msdcorr_nom    .append(jet_msdcorr_nom)
                jets_msdcorr_jerUp  .append(jet_pt_jerUpVal  *jet_msdcorr_jmrNomVal *jmsNomVal  *jet_msdcorr_raw)
                jets_msdcorr_jerDown.append(jet_pt_jerDownVal*jet_msdcorr_jmrNomVal *jmsNomVal  *jet_msdcorr_raw)
                jets_msdcorr_jmrUp  .append(jet_pt_jerNomVal *jet_msdcorr_jmrUpVal  *jmsNomVal  *jet_msdcorr_raw)
                jets_msdcorr_jmrDown.append(jet_pt_jerNomVal *jet_msdcorr_jmrDownVal*jmsNomVal  *jet_msdcorr_raw)
                jets_msdcorr_jmsUp  .append(jet_pt_jerNomVal *jet_msdcorr_jmrNomVal *jmsUpVal   *jet_msdcorr_raw)
                jets_msdcorr_jmsDown.append(jet_pt_jerNomVal *jet_msdcorr_jmrNomVal *jmsDownVal *jet_msdcorr_raw)

            
            for jesUncertainty in self.jesUncertainties:
                # (cf. https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookJetEnergyCorrections#JetCorUncertainties )
                self.jesUncertainty[jesUncertainty].setJetPt(jet_pt_nom)
                self.jesUncertainty[jesUncertainty].setJetEta(jet.eta)
                delta = self.jesUncertainty[jesUncertainty].getUncertainty(True)
                jet_pt_jesUp[jesUncertainty]   = jet_pt_nom*(1. + delta)
                jet_pt_jesDown[jesUncertainty] = jet_pt_nom*(1. - delta)
                jets_pt_jesUp[jesUncertainty].append(jet_pt_jesUp[jesUncertainty])
                jets_pt_jesDown[jesUncertainty].append(jet_pt_jesDown[jesUncertainty])
                jet_mass_jesUp   [jesUncertainty] = jet_mass_nom*(1. + delta)
                jet_mass_jesDown [jesUncertainty] = jet_mass_nom*(1. - delta)
                jets_mass_jesUp  [jesUncertainty].append(jet_mass_jesUp[jesUncertainty])
                jets_mass_jesDown[jesUncertainty].append(jet_mass_jesDown[jesUncertainty])
                if self.doGroomed :
                    jet_msdcorr_jesUp   [jesUncertainty] = jet_msdcorr_nom*(1. + delta)
                    jet_msdcorr_jesDown [jesUncertainty] = jet_msdcorr_nom*(1. - delta)
                    jets_msdcorr_jesUp  [jesUncertainty].append(jet_msdcorr_jesUp[jesUncertainty])
                    jets_msdcorr_jesDown[jesUncertainty].append(jet_msdcorr_jesDown[jesUncertainty])                    
                
                # redo JES variations for T1 MET
                self.jesUncertainty[jesUncertainty].setJetPt(jet_pt_L1L2L3)
                self.jesUncertainty[jesUncertainty].setJetEta(jet.eta)
                delta = self.jesUncertainty[jesUncertainty].getUncertainty(True)
                jet_pt_jesUpT1[jesUncertainty]   = jet_pt_L1L2L3*(1. + delta)
                jet_pt_jesDownT1[jesUncertainty] = jet_pt_L1L2L3*(1. - delta)


            # progate JER and JES corrections and uncertainties to MET
            if self.corrMET and jet_pt_L1L2L3 > self.unclEnThreshold and (jet.neEmEF+jet.chEmEF) < 0.9:
                if not ( self.metBranchName == 'METFixEE2017' and 2.65<abs(jet.eta)<3.14 and jet.pt*(1-jet.rawFactor)<50 ): # do not re-correct for jets that aren't included in METv2 recipe
                    jet_cosPhi = math.cos(jet.phi)
                    jet_sinPhi = math.sin(jet.phi)
                    #print "Correcting met_x %s by %s"%(met_px_nom, (jet_pt_nom - jet_pt_orig)*jet_cosPhi)
                    #print "Correcting met_y %s by %s"%(met_py_nom, (jet_pt_nom - jet_pt_orig)*jet_sinPhi)
                    #print jet_pt_T1, jet_pt_nom
                    met_px_nom     = met_px_nom     - (jet_pt_L1L2L3     - jet_pt_L1)*jet_cosPhi # correct from L1 level
                    met_py_nom     = met_py_nom     - (jet_pt_L1L2L3     - jet_pt_L1)*jet_sinPhi # correct from L1 level
                    met_px_jerUp   = met_px_jerUp   - (jet_pt_jerUp   - jet_pt_L1)*jet_cosPhi # needs to be checked/fixed. not used ATM
                    met_py_jerUp   = met_py_jerUp   - (jet_pt_jerUp   - jet_pt_L1)*jet_sinPhi # needs to be checked/fixed. not used ATM
                    met_px_jerDown = met_px_jerDown - (jet_pt_jerDown - jet_pt_L1)*jet_cosPhi # needs to be checked/fixed. not used ATM
                    met_py_jerDown = met_py_jerDown - (jet_pt_jerDown - jet_pt_L1)*jet_sinPhi # needs to be checked/fixed. not used ATM
                    for jesUncertainty in self.jesUncertainties:
                        met_px_jesUp[jesUncertainty]   = met_px_jesUp[jesUncertainty]   - (jet_pt_jesUpT1[jesUncertainty]   - jet_pt_L1)*jet_cosPhi
                        met_py_jesUp[jesUncertainty]   = met_py_jesUp[jesUncertainty]   - (jet_pt_jesUpT1[jesUncertainty]   - jet_pt_L1)*jet_sinPhi
                        met_px_jesDown[jesUncertainty] = met_px_jesDown[jesUncertainty] - (jet_pt_jesDownT1[jesUncertainty] - jet_pt_L1)*jet_cosPhi
                        met_py_jesDown[jesUncertainty] = met_py_jesDown[jesUncertainty] - (jet_pt_jesDownT1[jesUncertainty] - jet_pt_L1)*jet_sinPhi

        # propagate "unclustered energy" uncertainty to MET
        if self.corrMET :

            if self.metBranchName == 'METFixEE2017':
                # Remove the L1L2L3-L1 corrected jets in the EE region from the default MET branch
                def_met_px += delta_x_T1Jet
                def_met_py += delta_y_T1Jet

                # get unclustered energy part that is removed in the v2 recipe
                met_unclEE_x = def_met_px - t1met_px
                met_unclEE_y = def_met_py - t1met_py

                # finalize the v2 recipe for the rawMET by removing the unclustered part in the EE region
                met_px_nom += delta_x_rawJet - met_unclEE_x 
                met_py_nom += delta_y_rawJet - met_unclEE_y
                
                met_px_jerUp += delta_x_rawJet - met_unclEE_x
                met_py_jerUp += delta_y_rawJet - met_unclEE_y
                met_px_jerDown += delta_x_rawJet - met_unclEE_x
                met_py_jerDown += delta_y_rawJet - met_unclEE_y
                for jesUncertainty in self.jesUncertainties:
                    met_px_jesUp[jesUncertainty] += delta_x_rawJet - met_unclEE_x
                    met_py_jesUp[jesUncertainty] += delta_y_rawJet - met_unclEE_y
                    met_px_jesDown[jesUncertainty] += delta_x_rawJet - met_unclEE_x
                    met_py_jesDown[jesUncertainty] += delta_y_rawJet - met_unclEE_y
                

            ( met_px_unclEnUp,   met_py_unclEnUp   ) = ( met_px_nom, met_py_nom )
            ( met_px_unclEnDown, met_py_unclEnDown ) = ( met_px_nom, met_py_nom )
            met_deltaPx_unclEn = getattr(event, self.metBranchName + "_MetUnclustEnUpDeltaX")
            met_deltaPy_unclEn = getattr(event, self.metBranchName + "_MetUnclustEnUpDeltaY")
            met_px_unclEnUp    = met_px_unclEnUp   + met_deltaPx_unclEn
            met_py_unclEnUp    = met_py_unclEnUp   + met_deltaPy_unclEn
            met_px_unclEnDown  = met_px_unclEnDown - met_deltaPx_unclEn
            met_py_unclEnDown  = met_py_unclEnDown - met_deltaPy_unclEn

            ##### COMMENTED OUT - NO SMEARING USED ATM ####
            ## propagate effect of jet energy smearing to MET
            #met_px_jerUp   = met_px_jerUp   + (met_px_nom - met_px)
            #met_py_jerUp   = met_py_jerUp   + (met_py_nom - met_py)
            #met_px_jerDown = met_px_jerDown + (met_px_nom - met_px)
            #met_py_jerDown = met_py_jerDown + (met_py_nom - met_py)
            #for jesUncertainty in self.jesUncertainties:
            #    met_px_jesUp[jesUncertainty]   = met_px_jesUp[jesUncertainty]   + (met_px_nom - met_px)
            #    met_py_jesUp[jesUncertainty]   = met_py_jesUp[jesUncertainty]   + (met_py_nom - met_py)
            #    met_px_jesDown[jesUncertainty] = met_px_jesDown[jesUncertainty] + (met_px_nom - met_px)
            #    met_py_jesDown[jesUncertainty] = met_py_jesDown[jesUncertainty] + (met_py_nom - met_py)
            #met_px_unclEnUp    = met_px_unclEnUp   + (met_px_nom - met_px)
            #met_py_unclEnUp    = met_py_unclEnUp   + (met_py_nom - met_py)
            #met_px_unclEnDown  = met_px_unclEnDown + (met_px_nom - met_px)
            #met_py_unclEnDown  = met_py_unclEnDown + (met_py_nom - met_py)



            
        self.out.fillBranch("%s_pt_nom" % self.jetBranchName, jets_pt_nom)
        self.out.fillBranch("%s_corr_JEC" % self.jetBranchName, jets_corr_JEC)
        self.out.fillBranch("%s_corr_JER" % self.jetBranchName, jets_corr_JER)
        self.out.fillBranch("%s_pt_jerUp" % self.jetBranchName, jets_pt_jerUp)
        self.out.fillBranch("%s_pt_jerDown" % self.jetBranchName, jets_pt_jerDown)
        self.out.fillBranch("%s_mass_nom" % self.jetBranchName, jets_mass_nom)
        self.out.fillBranch("%s_mass_jerUp" % self.jetBranchName, jets_mass_jerUp)
        self.out.fillBranch("%s_mass_jerDown" % self.jetBranchName, jets_mass_jerDown)
        self.out.fillBranch("%s_mass_jmrUp" % self.jetBranchName, jets_mass_jmrUp)
        self.out.fillBranch("%s_mass_jmrDown" % self.jetBranchName, jets_mass_jmrDown)
        self.out.fillBranch("%s_mass_jmsUp" % self.jetBranchName, jets_mass_jmsUp)
        self.out.fillBranch("%s_mass_jmsDown" % self.jetBranchName, jets_mass_jmsDown)
            
        if self.doGroomed :

            self.out.fillBranch("%s_msoftdrop_nom" % self.jetBranchName, jets_msdcorr_nom)
            self.out.fillBranch("%s_msoftdrop_jerUp" % self.jetBranchName, jets_msdcorr_jerUp)
            self.out.fillBranch("%s_msoftdrop_jerDown" % self.jetBranchName, jets_msdcorr_jerDown)
            self.out.fillBranch("%s_msoftdrop_jmrUp" % self.jetBranchName, jets_msdcorr_jmrUp)
            self.out.fillBranch("%s_msoftdrop_jmrDown" % self.jetBranchName, jets_msdcorr_jmrDown)
            self.out.fillBranch("%s_msoftdrop_jmsUp" % self.jetBranchName, jets_msdcorr_jmsUp)
            self.out.fillBranch("%s_msoftdrop_jmsDown" % self.jetBranchName, jets_msdcorr_jmsDown)

            
        if self.corrMET :
            self.out.fillBranch("%s_pt_nom" % self.metBranchName, math.sqrt(met_px_nom**2 + met_py_nom**2))
            self.out.fillBranch("%s_phi_nom" % self.metBranchName, math.atan2(met_py_nom, met_px_nom))        
            self.out.fillBranch("%s_pt_jerUp" % self.metBranchName, math.sqrt(met_px_jerUp**2 + met_py_jerUp**2))
            self.out.fillBranch("%s_phi_jerUp" % self.metBranchName, math.atan2(met_py_jerUp, met_px_jerUp))        
            self.out.fillBranch("%s_pt_jerDown" % self.metBranchName, math.sqrt(met_px_jerDown**2 + met_py_jerDown**2))
            self.out.fillBranch("%s_phi_jerDown" % self.metBranchName, math.atan2(met_py_jerDown, met_px_jerDown))
            
        for jesUncertainty in self.jesUncertainties:
            self.out.fillBranch("%s_pt_jes%sUp" % (self.jetBranchName, jesUncertainty), jets_pt_jesUp[jesUncertainty])
            self.out.fillBranch("%s_pt_jes%sDown" % (self.jetBranchName, jesUncertainty), jets_pt_jesDown[jesUncertainty])
            self.out.fillBranch("%s_mass_jes%sUp" % (self.jetBranchName, jesUncertainty), jets_mass_jesUp[jesUncertainty])
            self.out.fillBranch("%s_mass_jes%sDown" % (self.jetBranchName, jesUncertainty), jets_mass_jesDown[jesUncertainty])
            
            if self.doGroomed : 
                self.out.fillBranch("%s_msoftdrop_jes%sUp" % (self.jetBranchName, jesUncertainty), jets_msdcorr_jesUp[jesUncertainty])
                self.out.fillBranch("%s_msoftdrop_jes%sDown" % (self.jetBranchName, jesUncertainty), jets_msdcorr_jesDown[jesUncertainty])
                
            
            if self.corrMET:
                self.out.fillBranch("%s_pt_jes%sUp" % (self.metBranchName, jesUncertainty), math.sqrt(met_px_jesUp[jesUncertainty]**2 + met_py_jesUp[jesUncertainty]**2))
                self.out.fillBranch("%s_phi_jes%sUp" % (self.metBranchName, jesUncertainty), math.atan2(met_py_jesUp[jesUncertainty], met_px_jesUp[jesUncertainty]))
                self.out.fillBranch("%s_pt_jes%sDown" % (self.metBranchName, jesUncertainty), math.sqrt(met_px_jesDown[jesUncertainty]**2 + met_py_jesDown[jesUncertainty]**2))
                self.out.fillBranch("%s_phi_jes%sDown" % (self.metBranchName, jesUncertainty), math.atan2(met_py_jesDown[jesUncertainty], met_px_jesDown[jesUncertainty]))
        if self.corrMET:
            self.out.fillBranch("%s_pt_unclustEnUp" % self.metBranchName, math.sqrt(met_px_unclEnUp**2 + met_py_unclEnUp**2))
            self.out.fillBranch("%s_phi_unclustEnUp" % self.metBranchName, math.atan2(met_py_unclEnUp, met_px_unclEnUp))
            self.out.fillBranch("%s_pt_unclustEnDown" % self.metBranchName, math.sqrt(met_px_unclEnDown**2 + met_py_unclEnDown**2))
            self.out.fillBranch("%s_phi_unclustEnDown" % self.metBranchName, math.atan2(met_py_unclEnDown, met_px_unclEnDown))

        return True

# define modules using the syntax 'name = lambda : constructor' to avoid having them loaded when not needed

jetmetUncertainties2016 = lambda : jetmetUncertaintiesProducer("2016", "Summer16_23Sep2016V4_MC", [ "Total" ])
jetmetUncertainties2016All = lambda : jetmetUncertaintiesProducer("2016", "Summer16_23Sep2016V4_MC", [ "All" ])
jetmetUncertainties2017 = lambda : jetmetUncertaintiesProducer("2017", "Fall17_17Nov2017_V6_MC", [ "Total" ])
jetmetUncertainties2017All = lambda : jetmetUncertaintiesProducer("2017", "Fall17_17Nov2017_V6_MC", [ "All" ], redoJEC=True)

jetmetUncertainties2016AK4Puppi = lambda : jetmetUncertaintiesProducer("2016", "Summer16_23Sep2016V4_MC", [ "Total" ], jetType="AK4PFPuppi")
jetmetUncertainties2016AK4PuppiAll = lambda : jetmetUncertaintiesProducer("2016", "Summer16_23Sep2016V4_MC",  [ "All" ], jetType="AK4PFPuppi")
jetmetUncertainties2017AK4Puppi = lambda : jetmetUncertaintiesProducer("2017", "Fall17_17Nov2017_V6_MC", [ "Total" ], jetType="AK4PFPuppi")
jetmetUncertainties2017AK4PuppiAll = lambda : jetmetUncertaintiesProducer("2017", "Fall17_17Nov2017_V6_MC",  [ "All" ], jetType="AK4PFPuppi")

jetmetUncertainties2016AK8Puppi = lambda : jetmetUncertaintiesProducer("2016", "Summer16_23Sep2016V4_MC", [ "Total" ], jetType="AK8PFPuppi")
jetmetUncertainties2016AK8PuppiAll = lambda : jetmetUncertaintiesProducer("2016", "Summer16_23Sep2016V4_MC",  [ "All" ], jetType="AK8PFPuppi")
jetmetUncertainties2016AK8PuppiNoGroom = lambda : jetmetUncertaintiesProducer("2016", "Summer16_23Sep2016V4_MC", [ "Total" ], jetType="AK8PFPuppi",redoJEC=False,noGroom=True)
jetmetUncertainties2016AK8PuppiAllNoGroom = lambda : jetmetUncertaintiesProducer("2016", "Summer16_23Sep2016V4_MC", ["All"], jetType="AK8PFPuppi",redoJEC=False,noGroom=True)
jetmetUncertainties2017AK8Puppi = lambda : jetmetUncertaintiesProducer("2017", "Fall17_17Nov2017_V6_MC", [ "Total" ], jetType="AK8PFPuppi")
jetmetUncertainties2017AK8PuppiAll = lambda : jetmetUncertaintiesProducer("2017", "Fall17_17Nov2017_V6_MC", ["All"], jetType="AK8PFPuppi")
