#!/pxrpythonsubst
#
# Copyright 2017 Pixar
#
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
# compliance with the Apache License and the following modification to it:
# Section 6. Trademarks. is deleted and replaced with:
#
# 6. Trademarks. This License does not grant permission to use the trade
#    names, trademarks, service marks, or product names of the Licensor
#    and its affiliates, except as required to comply with Section 4(c) of
#    the License and to reproduce the content of the NOTICE file.
#
# You may obtain a copy of the Apache License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.

from pxr import Usd, UsdSkel, UsdGeom, Vt, Sdf
import unittest


class TestUsdSkelCache(unittest.TestCase):


    def test_AnimQuery(self):
        """Tests anim query retrieval."""

        cache = UsdSkel.Cache()

        stage = Usd.Stage.CreateInMemory()
         
        anim = UsdSkel.Animation.Define(stage, "/Anim")

        self.assertTrue(cache.GetAnimQuery(anim))
        # Backwards-compatibility.
        self.assertTrue(cache.GetAnimQuery(prim=anim.GetPrim()))

        self.assertFalse(cache.GetAnimQuery(UsdSkel.Animation()))

        # TODO: Test query of anim behind instancing

    
    def test_InheritedAnimBinding(self):
        """Tests for correctness in the interpretation of the inherited
           skel:animationSource binding."""
        
        testFile = "populate.usda"
        stage = Usd.Stage.Open(testFile)

        cache = UsdSkel.Cache()
        root = UsdSkel.Root(stage.GetPrimAtPath("/AnimBinding"))
        self.assertTrue(cache.Populate(root))

        query = cache.GetSkelQuery(
            UsdSkel.Skeleton.Get(stage, "/AnimBinding/Scope/Inherit"))
        self.assertTrue(query)
        self.assertEqual(query.GetAnimQuery().GetPrim().GetPath(),
                         Sdf.Path("/Anim1"))

        query = cache.GetSkelQuery(
            UsdSkel.Skeleton.Get(stage, "/AnimBinding/Scope/Override"))
        self.assertTrue(query)
        self.assertEqual(query.GetAnimQuery().GetPrim().GetPath(),
                         Sdf.Path("/Anim2"))

        query = cache.GetSkelQuery(
            UsdSkel.Skeleton.Get(stage, "/AnimBinding/Scope/Block"))
        self.assertTrue(query)
        self.assertFalse(query.GetAnimQuery())
        
        query = cache.GetSkelQuery(
            UsdSkel.Skeleton.Get(stage, "/AnimBinding/Unbound"))
        self.assertTrue(query)
        self.assertFalse(query.GetAnimQuery())

        query = cache.GetSkelQuery(
            UsdSkel.Skeleton.Get(stage, "/AnimBinding/BoundToInactiveAnim"))
        self.assertTrue(query)
        self.assertFalse(query.GetAnimQuery())

        # Ensure that the animationSource binding crosses instancing arcs.

        query = cache.GetSkelQuery(
            UsdSkel.Skeleton.Get(stage, "/AnimBinding/Instance/Inherit"))
        self.assertTrue(query)
        self.assertEqual(query.GetAnimQuery().GetPrim().GetPath(),
                         Sdf.Path("/Anim1"))

        # TODO: This test case is failing:
        query = cache.GetSkelQuery(
            UsdSkel.Skeleton.Get(stage, "/AnimBinding/Instance/Override"))
        self.assertTrue(query)
        self.assertTrue(query.GetAnimQuery().GetPrim().IsInMaster())


    def test_InheritedSkeletonBinding(self):
        """Tests for correctness in the interpretation of the inherited
           skel:skeleton binding."""

        testFile = "populate.usda"
        stage = Usd.Stage.Open(testFile)

        cache = UsdSkel.Cache()
        self.assertFalse(cache.IncludesInstances())

        root = UsdSkel.Root(stage.GetPrimAtPath("/SkelBinding"))
        self.assertTrue(cache.Populate(root))

        skel1 = UsdSkel.Skeleton.Get(stage, "/Skel1")
        skel2 = UsdSkel.Skeleton.Get(stage, "/Skel2")

        binding1 = cache.ComputeSkelBinding(root, skel1)
        self.assertEqual(binding1.GetSkeleton().GetPrim(), skel1.GetPrim())
        self.assertEqual(len(binding1.GetSkinningTargets()), 1)
        skinningQuery1 = binding1.GetSkinningTargets()[0]
        self.assertEqual(skinningQuery1.GetPrim().GetPath(),
                         Sdf.Path("/SkelBinding/Scope/Inherit"))
        # Inherited skinning properties.
        self.assertEqual(skinningQuery1.GetJointIndicesPrimvar()
                         .GetAttr().GetPath().GetPrimPath(),
                         Sdf.Path("/SkelBinding/Scope"))
        self.assertEqual(skinningQuery1.GetJointWeightsPrimvar()
                         .GetAttr().GetPath().GetPrimPath(),
                         Sdf.Path("/SkelBinding/Scope"))
        self.assertEqual(skinningQuery1.GetJointOrder(),
                         Vt.TokenArray(["scope"]))
        # Non-inherited skinning properties.
        self.assertFalse(skinningQuery1.GetBlendShapesAttr())
        self.assertFalse(skinningQuery1.GetBlendShapeTargetsRel())

        binding2 = cache.ComputeSkelBinding(root, skel2)
        self.assertEqual(binding2.GetSkeleton().GetPrim(), skel2.GetPrim())
        self.assertEqual(len(binding2.GetSkinningTargets()), 1)
        skinningQuery2 = binding2.GetSkinningTargets()[0]
        self.assertEqual(skinningQuery2.GetPrim().GetPath(),
                         Sdf.Path("/SkelBinding/Scope/Override"))
        # Inherited skinning properties.
        self.assertEqual(skinningQuery2.GetPrim().GetPath(),
                         Sdf.Path("/SkelBinding/Scope/Override"))
        self.assertEqual(skinningQuery2.GetJointIndicesPrimvar()
                         .GetAttr().GetPath().GetPrimPath(),
                         Sdf.Path("/SkelBinding/Scope/Override"))
        self.assertEqual(skinningQuery2.GetJointWeightsPrimvar()
                         .GetAttr().GetPath().GetPrimPath(),
                         Sdf.Path("/SkelBinding/Scope/Override"))
        self.assertEqual(skinningQuery2.GetJointOrder(),
                         Vt.TokenArray(["override"]))
        # Non-inherited skinning properties.
        self.assertEqual(skinningQuery2.GetBlendShapesAttr()
                         .GetPath().GetPrimPath(),
                         Sdf.Path("/SkelBinding/Scope/Override"))
        self.assertEqual(skinningQuery2.GetBlendShapeTargetsRel()
                         .GetPath().GetPrimPath(),
                         Sdf.Path("/SkelBinding/Scope/Override"))

        allBindings = cache.ComputeSkelBindings(root)
        # Expecting two resolved bindings. This should *not* include bindings
        # for any inactive skels or instances
        self.assertEqual(len(allBindings), 2)

        self.assertEqual(binding1.GetSkeleton().GetPrim(),
                         allBindings[0].GetSkeleton().GetPrim())
        self.assertEqual([t.GetPrim() for t in binding1.GetSkinningTargets()],
                         [t.GetPrim() for t in allBindings[0].GetSkinningTargets()])

        self.assertEqual(binding2.GetSkeleton().GetPrim(),
                         allBindings[1].GetSkeleton().GetPrim())
        self.assertEqual([t.GetPrim() for t in binding2.GetSkinningTargets()],
                         [t.GetPrim() for t in allBindings[1].GetSkinningTargets()])


    def test_InstancedSkeletonBinding(self):
        """Tests for correctness in the interpretation of the inherited
           skel:skeleton binding with instancing."""

        testFile = "populate.usda"
        stage = Usd.Stage.Open(testFile)

        cache = UsdSkel.Cache(includeInstances=True)
        self.assertTrue(cache.IncludesInstances())

        root = UsdSkel.Root(stage.GetPrimAtPath("/SkelBinding"))
        self.assertTrue(cache.Populate(root))

        skel1 = UsdSkel.Skeleton.Get(stage, "/Skel1")

        binding1 = cache.ComputeSkelBinding(root, skel1)
        self.assertEqual(binding1.GetSkeleton().GetPrim(), skel1.GetPrim())
        self.assertEqual(len(binding1.GetSkinningTargets()), 2)
        skinningQuery1 = binding1.GetSkinningTargets()[1]
        self.assertEqual(skinningQuery1.GetPrim().GetPath(),
                         Sdf.Path("/SkelBinding/Instance/Inherit"))
        # Inherited skinning properties.
        self.assertEqual(skinningQuery1.GetJointIndicesPrimvar()
                         .GetAttr().GetPath().GetPrimPath(),
                         Sdf.Path("/SkelBinding/Instance"))
        self.assertEqual(skinningQuery1.GetJointWeightsPrimvar()
                         .GetAttr().GetPath().GetPrimPath(),
                         Sdf.Path("/SkelBinding/Instance"))
        self.assertEqual(skinningQuery1.GetJointOrder(),
                         Vt.TokenArray(["instance"]))
        # Non-inherited skinning properties.
        self.assertFalse(skinningQuery1.GetBlendShapesAttr())
        self.assertFalse(skinningQuery1.GetBlendShapeTargetsRel())

        allBindings = cache.ComputeSkelBindings(root)
        # Expecting three resolved bindings. This should *not* include bindings
        # for any inactive skels, but does include instances
        self.assertEqual(len(allBindings), 3)

        skel2 = UsdSkel.Skeleton.Get(stage, "/SkelBinding/Instance/Skel")
        binding2 = cache.ComputeSkelBinding(root, skel2)

        self.assertEqual(binding2.GetSkeleton().GetPrim(),
                         allBindings[2].GetSkeleton().GetPrim())
        self.assertEqual([t.GetPrim() for t in binding2.GetSkinningTargets()],
                         [t.GetPrim() for t in allBindings[2].GetSkinningTargets()])



if __name__ == "__main__":
    unittest.main()
