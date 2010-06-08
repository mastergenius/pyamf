# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for L{ClassAlias} and L{register_class}. Both are the most
fundamental parts of PyAMF and the test suite for it is big so it makes sense
to have them in one file.

@since: 0.5
"""

import unittest

import pyamf
from pyamf import ClassAlias
from pyamf.tests.util import ClassCacheClearingTestCase, Spam, get_fqcn

try:
    set
except NameError:
    from sets import Set as set


class ClassAliasTestCase(ClassCacheClearingTestCase):
    """
    Test all functionality relating to the class L{ClassAlias}.
    """

    def test_init(self):
        x = ClassAlias(Spam)

        self.assertTrue(x.anonymous)
        self.assertTrue(x.dynamic)
        self.assertFalse(x.amf3)
        self.assertFalse(x.external)

        self.assertEquals(x.readonly_attrs, None)
        self.assertEquals(x.static_attrs, None)
        self.assertEquals(x.exclude_attrs, None)
        self.assertEquals(x.proxy_attrs, None)

        self.assertEquals(x.alias, '')
        self.assertEquals(x.klass, Spam)

        # compiled attributes
        self.assertEquals(x.decodable_properties, None)
        self.assertEquals(x.encodable_properties, None)
        self.assertTrue(x._compiled)

    def test_init_deferred(self):
        """
        Test for initial deferred compliation
        """
        x = ClassAlias(Spam, defer=True)

        self.assertTrue(x.anonymous)
        self.assertEquals(x.dynamic, None)
        self.assertFalse(x.amf3)
        self.assertFalse(x.external)

        self.assertEquals(x.readonly_attrs, None)
        self.assertEquals(x.static_attrs, None)
        self.assertEquals(x.exclude_attrs, None)
        self.assertEquals(x.proxy_attrs, None)

        self.assertEquals(x.alias, '')
        self.assertEquals(x.klass, Spam)

        # compiled attributes
        self.assertFalse(hasattr(x, 'static_properties'))
        self.assertFalse(x._compiled)

    def test_init_kwargs(self):
        x = ClassAlias(Spam, alias='foo', static_attrs=('bar',),
            exclude_attrs=('baz',), readonly_attrs='gak', amf3='spam',
            external='eggs', dynamic='goo', proxy_attrs=('blarg',))

        self.assertFalse(x.anonymous)
        self.assertEquals(x.dynamic, 'goo')
        self.assertEquals(x.amf3, 'spam')
        self.assertEquals(x.external, 'eggs')

        self.assertEquals(x.readonly_attrs, ['a', 'g', 'k'])
        self.assertEquals(x.static_attrs, ['bar'])
        self.assertEquals(x.exclude_attrs, ['baz'])
        self.assertEquals(x.proxy_attrs, ['blarg'])

        self.assertEquals(x.alias, 'foo')
        self.assertEquals(x.klass, Spam)

        # compiled attributes
        self.assertEquals(x.encodable_properties, ['bar'])
        self.assertEquals(x.decodable_properties, ['bar'])
        self.assertTrue(x._compiled)

    def test_bad_class(self):
        self.assertRaises(TypeError, ClassAlias, 'eggs', 'blah')

    def test_init_args(self):
        class ClassicFoo:
            def __init__(self, foo, bar):
                pass

        class NewFoo(object):
            def __init__(self, foo, bar):
                pass

        self.assertRaises(TypeError, ClassAlias, ClassicFoo)
        ClassAlias(NewFoo)

    def test_createInstance(self):
        x = ClassAlias(Spam, 'org.example.spam.Spam')

        y = x.createInstance()

        self.assertTrue(isinstance(y, Spam))

    def test_str(self):
        class Eggs(object):
            pass

        x = ClassAlias(Eggs, 'org.example.eggs.Eggs')

        self.assertEquals(str(x), 'org.example.eggs.Eggs')

    def test_eq(self):
        class A(object):
            pass

        class B(object):
            pass

        x = ClassAlias(A, 'org.example.A')
        y = ClassAlias(A, 'org.example.A')
        z = ClassAlias(B, 'org.example.B')

        self.assertEquals(x, A)
        self.assertEquals(x, y)
        self.assertNotEquals(x, z)


class GetEncodableAttributesTestCase(unittest.TestCase):
    """
    Tests for L{ClassAlias.getEncodableAttributes}
    """

    def setUp(self):
        self.alias = ClassAlias(Spam, 'foo', defer=True)
        self.obj = Spam()

    def test_empty(self):
        attrs = self.alias.getEncodableAttributes(self.obj)

        self.assertEquals(attrs, {})

    def test_static(self):
        self.alias.static_attrs = ['foo', 'bar']
        self.alias.compile()

        self.obj.foo = 'bar'
        # leave self.obj.bar
        self.assertFalse(hasattr(self.obj, 'bar'))

        attrs = self.alias.getEncodableAttributes(self.obj)

        self.assertEquals(attrs, {'foo': 'bar', 'bar': pyamf.Undefined})

    def test_not_dynamic(self):
        self.alias.compile()
        self.alias.dynamic = False

        self.assertEquals(self.alias.getEncodableAttributes(self.obj), {})

    def test_dynamic(self):
        self.alias.compile()

        self.assertEquals(self.alias.encodable_properties, None)
        self.obj.foo = 'bar'
        self.obj.bar = 'foo'

        attrs = self.alias.getEncodableAttributes(self.obj)
        self.assertEquals(attrs, {'foo': 'bar', 'bar': 'foo'})

    def test_proxy(self):
        from pyamf import flex

        codec = pyamf.BaseEncoder()

        self.alias.proxy_attrs = ('foo', 'bar')
        self.alias.compile()

        self.assertEquals(self.alias.proxy_attrs, ['bar', 'foo'])

        self.obj.foo = ['bar', 'baz']
        self.obj.bar = {'foo': 'gak'}

        attrs = self.alias.getEncodableAttributes(self.obj, codec)

        k = attrs.keys()

        k.sort()

        self.assertEquals(k, ['bar', 'foo'])

        self.assertTrue(isinstance(attrs['foo'], flex.ArrayCollection))
        self.assertEquals(attrs['foo'], ['bar', 'baz'])

        self.assertTrue(isinstance(attrs['bar'], flex.ObjectProxy))
        self.assertEquals(attrs['bar']._amf_object, {'foo': 'gak'})


class GetDecodableAttributesTestCase(unittest.TestCase):
    """
    Tests for L{ClassAlias.getDecodableAttributes}
    """

    def setUp(self):
        self.alias = ClassAlias(Spam, 'foo', defer=True)
        self.obj = Spam()

    def test_compile(self):
        self.assertFalse(self.alias._compiled)

        self.alias.applyAttributes(self.obj, {})

        self.assertTrue(self.alias._compiled)

    def test_missing_static_property(self):
        self.alias.static_attrs = ['foo', 'bar']
        self.alias.compile()

        attrs = {'foo': None} # missing bar key ..

        self.assertRaises(AttributeError, self.alias.getDecodableAttributes,
            self.obj, attrs)

    def test_no_static(self):
        self.alias.compile()

        attrs = {'foo': None, 'bar': [1, 2, 3]}

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(attrs, {'foo': None, 'bar': [1, 2, 3]})

    def test_readonly(self):
        self.alias.compile()

        self.alias.readonly_attrs = ['bar']

        attrs = {'foo': None, 'bar': [1, 2, 3]}

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {'foo': None})

    def test_not_dynamic(self):
        self.alias.compile()

        self.alias.decodable_properties = set(['bar'])
        self.alias.dynamic = False

        attrs = {'foo': None, 'bar': [1, 2, 3]}

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {'bar': [1, 2, 3]})

    def test_dynamic(self):
        self.alias.compile()

        self.alias.static_properties = ['bar']
        self.alias.dynamic = True

        attrs = {'foo': None, 'bar': [1, 2, 3]}

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {'foo': None, 'bar': [1, 2, 3]})

    def test_complex(self):
        self.alias.compile()

        self.alias.static_properties = ['foo', 'bar']
        self.alias.exclude_attrs = ['baz', 'gak']
        self.alias.readonly_attrs = ['spam', 'eggs']

        attrs = {
            'foo': 'foo',
            'bar': 'bar',
            'baz': 'baz',
            'gak': 'gak',
            'spam': 'spam',
            'eggs': 'eggs',
            'dyn1': 'dyn1',
            'dyn2': 'dyn2'
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {
            'foo': 'foo',
            'bar': 'bar',
            'dyn2': 'dyn2',
            'dyn1': 'dyn1'
        })

    def test_complex_not_dynamic(self):
        self.alias.compile()

        self.alias.decodable_properties = ['foo', 'bar']
        self.alias.exclude_attrs = ['baz', 'gak']
        self.alias.readonly_attrs = ['spam', 'eggs']
        self.alias.dynamic = False

        attrs = {
            'foo': 'foo',
            'bar': 'bar',
            'baz': 'baz',
            'gak': 'gak',
            'spam': 'spam',
            'eggs': 'eggs',
            'dyn1': 'dyn1',
            'dyn2': 'dyn2'
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {'foo': 'foo', 'bar': 'bar'})

    def test_static(self):
        self.alias.dynamic = False
        self.alias.compile()

        self.alias.decodable_properties = set(['foo', 'bar'])

        attrs = {
            'foo': 'foo',
            'bar': 'bar',
            'baz': 'baz',
            'gak': 'gak',
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {'foo': 'foo', 'bar': 'bar'})

    def test_proxy(self):
        from pyamf import flex

        codec = pyamf.BaseEncoder()

        self.alias.proxy_attrs = ('foo', 'bar')
        self.alias.compile()

        self.assertEquals(self.alias.proxy_attrs, ['bar', 'foo'])

        attrs = {
            'foo': flex.ArrayCollection(['bar', 'baz']),
            'bar': flex.ObjectProxy({'foo': 'gak'})
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs, codec)

        self.assertEquals(ret, {
            'foo': ['bar', 'baz'],
            'bar': {'foo': 'gak'}
        })

    def test_synonym(self):
        self.alias.synonym_attrs = {'foo': 'bar'}
        self.alias.compile()

        self.assertFalse(self.alias.shortcut_encode)
        self.assertFalse(self.alias.shortcut_decode)

        attrs = {
            'foo': 'foo',
            'spam': 'eggs'
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {'bar': 'foo', 'spam': 'eggs'})


class ApplyAttributesTestCase(unittest.TestCase):
    """
    Tests for L{ClassAlias.applyAttributes}
    """

    def setUp(self):
        self.alias = ClassAlias(Spam, 'foo', defer=True)
        self.obj = Spam()

    def test_object(self):
        class Foo(object):
            pass

        attrs = {'foo': 'spam', 'bar': 'eggs'}
        self.obj = Foo()
        self.alias = ClassAlias(Foo, 'foo', defer=True)

        self.assertEquals(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEquals(self.obj.__dict__, {'foo': 'spam', 'bar': 'eggs'})

    def test_classic(self):
        class Foo:
            pass

        attrs = {'foo': 'spam', 'bar': 'eggs'}
        self.obj = Foo()
        self.alias = ClassAlias(Foo, 'foo', defer=True)

        self.assertEquals(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEquals(self.obj.__dict__, {'foo': 'spam', 'bar': 'eggs'})

    def test_readonly(self):
        self.alias.readonly_attrs = ['foo', 'bar']

        attrs = {'foo': 'spam', 'bar': 'eggs'}

        self.assertEquals(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEquals(self.obj.__dict__, {})

    def test_exclude(self):
        self.alias.exclude_attrs = ['foo', 'bar']

        attrs = {'foo': 'spam', 'bar': 'eggs'}

        self.assertEquals(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEquals(self.obj.__dict__, {})

    def test_not_dynamic(self):
        self.alias.static_properties = None
        self.alias.dynamic = False

        attrs = {'foo': 'spam', 'bar': 'eggs'}

        self.assertEquals(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEquals(self.obj.__dict__, {})

    def test_dict(self):
        attrs = {'foo': 'spam', 'bar': 'eggs'}
        self.obj = Spam()

        self.assertEquals(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEquals(self.obj.__dict__, {'foo': 'spam', 'bar': 'eggs'})


class SimpleCompliationTestCase(unittest.TestCase):
    """
    Tests for L{ClassAlias} property compliation for no inheritance.
    """

    def test_compiled(self):
        x = ClassAlias(Spam, defer=True)

        self.assertFalse(x._compiled)

        x._compiled = True
        o = x.static_properties = object()

        x.compile()

        self.assertTrue(o is x.static_properties)

    def test_external(self):
        class A(object):
            pass

        class B:
            pass

        self.assertRaises(AttributeError, ClassAlias, A, external=True)
        self.assertRaises(AttributeError, ClassAlias, B, external=True)

        A.__readamf__ = None
        B.__readamf__ = None

        self.assertRaises(AttributeError, ClassAlias, A, external=True)
        self.assertRaises(AttributeError, ClassAlias, B, external=True)

        A.__readamf__ = lambda x: None
        B.__readamf__ = lambda x: None

        self.assertRaises(AttributeError, ClassAlias, A, external=True)
        self.assertRaises(AttributeError, ClassAlias, B, external=True)

        A.__writeamf__ = 'foo'
        B.__writeamf__ = 'bar'

        self.assertRaises(TypeError, ClassAlias, A, external=True)
        self.assertRaises(TypeError, ClassAlias, B, external=True)

        A.__writeamf__ = lambda x: None
        B.__writeamf__ = lambda x: None

        a = ClassAlias(A, external=True)
        b = ClassAlias(B, external=True)

        self.assertEquals(a.readonly_attrs, None)
        self.assertEquals(a.static_attrs, None)
        self.assertEquals(a.decodable_properties, None)
        self.assertEquals(a.encodable_properties, None)
        self.assertEquals(a.exclude_attrs, None)

        self.assertTrue(a.anonymous)
        self.assertTrue(a.external)
        self.assertTrue(a._compiled)

        self.assertEquals(a.klass, A)
        self.assertEquals(a.alias, '')

        # now b

        self.assertEquals(b.readonly_attrs, None)
        self.assertEquals(b.static_attrs, None)
        self.assertEquals(b.decodable_properties, None)
        self.assertEquals(b.encodable_properties, None)
        self.assertEquals(b.exclude_attrs, None)

        self.assertTrue(b.anonymous)
        self.assertTrue(b.external)
        self.assertTrue(b._compiled)

        self.assertEquals(b.klass, B)
        self.assertEquals(b.alias, '')

    def test_anonymous(self):
        x = ClassAlias(Spam, None)

        x.compile()

        self.assertTrue(x.anonymous)
        self.assertTrue(x._compiled)

        self.assertEquals(x.klass, Spam)
        self.assertEquals(x.alias, '')

    def test_exclude(self):
        x = ClassAlias(Spam, exclude_attrs=['foo', 'bar'], defer=True)

        self.assertEquals(x.exclude_attrs, ['foo', 'bar'])

        x.compile()

        self.assertEquals(x.exclude_attrs, ['bar', 'foo'])

    def test_readonly(self):
        x = ClassAlias(Spam, readonly_attrs=['foo', 'bar'], defer=True)

        self.assertEquals(x.readonly_attrs, ['foo', 'bar'])

        x.compile()

        self.assertEquals(x.readonly_attrs, ['bar', 'foo'])

    def test_static(self):
        x = ClassAlias(Spam, static_attrs=['foo', 'bar'], defer=True)

        self.assertEquals(x.static_attrs, ['foo', 'bar'])

        x.compile()

        self.assertEquals(x.static_attrs, ['bar', 'foo'])

    def test_custom_properties(self):
        class A(ClassAlias):
            def getCustomProperties(self):
                self.encodable_properties.update(['foo', 'bar'])
                self.decodable_properties.update(['bar', 'foo'])

        a = A(Spam)

        self.assertEquals(a.encodable_properties, ['bar', 'foo'])
        self.assertEquals(a.decodable_properties, ['bar', 'foo'])

        # test combined
        b = A(Spam, static_attrs=['foo', 'baz', 'gak'])

        self.assertEquals(b.encodable_properties, ['bar', 'baz', 'foo', 'gak'])
        self.assertEquals(b.decodable_properties, ['bar', 'baz', 'foo', 'gak'])

    def test_amf3(self):
        x = ClassAlias(Spam, amf3=True)
        self.assertTrue(x.amf3)

    def test_dynamic(self):
        x = ClassAlias(Spam, dynamic=True)
        self.assertTrue(x.dynamic)

        x = ClassAlias(Spam, dynamic=False)
        self.assertFalse(x.dynamic)

        x = ClassAlias(Spam)
        self.assertTrue(x.dynamic)

    def test_sealed_external(self):
        class A(object):
            __slots__ = ('foo',)

            class __amf__:
                external = True

            def __readamf__(self, foo):
                pass

            def __writeamf__(self, foo):
                pass

        x = ClassAlias(A)

        x.compile()

        self.assertTrue(x.sealed)

    def test_synonym_attrs(self):
        x = ClassAlias(Spam, synonym_attrs={'foo': 'bar'}, defer=True)

        self.assertEquals(x.synonym_attrs, {'foo': 'bar'})

        x.compile()

        self.assertEquals(x.synonym_attrs, {'foo': 'bar'})


class CompilationInheritanceTestCase(ClassCacheClearingTestCase):
    """
    """

    def _register(self, alias):
        pyamf.CLASS_CACHE[get_fqcn(alias.klass)] = alias
        pyamf.CLASS_CACHE[alias.klass] = alias

        return alias

    def test_bases(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', defer=True))

        self.assertEquals(a.bases, None)
        self.assertEquals(b.bases, None)
        self.assertEquals(c.bases, None)

        a.compile()
        self.assertEquals(a.bases, [])

        b.compile()
        self.assertEquals(a.bases, [])
        self.assertEquals(b.bases, [(A, a)])

        c.compile()
        self.assertEquals(a.bases, [])
        self.assertEquals(b.bases, [(A, a)])
        self.assertEquals(c.bases, [(B, b), (A, a)])


    def test_exclude_classic(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', exclude_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', exclude_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEquals(a.exclude_attrs, ['foo'])
        self.assertEquals(b.exclude_attrs, ['foo'])
        self.assertEquals(c.exclude_attrs, ['bar', 'foo'])

    def test_exclude_new(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', exclude_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', exclude_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEquals(a.exclude_attrs, ['foo'])
        self.assertEquals(b.exclude_attrs, ['foo'])
        self.assertEquals(c.exclude_attrs, ['bar', 'foo'])

    def test_readonly_classic(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', readonly_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', readonly_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEquals(a.readonly_attrs, ['foo'])
        self.assertEquals(b.readonly_attrs, ['foo'])
        self.assertEquals(c.readonly_attrs, ['bar', 'foo'])

    def test_readonly_new(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', readonly_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', readonly_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEquals(a.readonly_attrs, ['foo'])
        self.assertEquals(b.readonly_attrs, ['foo'])
        self.assertEquals(c.readonly_attrs, ['bar', 'foo'])

    def test_static_classic(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', static_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', static_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEquals(a.static_attrs, ['foo'])
        self.assertEquals(b.static_attrs, ['foo'])
        self.assertEquals(c.static_attrs, ['bar', 'foo'])

    def test_static_new(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', static_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', static_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEquals(a.static_attrs, ['foo'])
        self.assertEquals(b.static_attrs, ['foo'])
        self.assertEquals(c.static_attrs, ['bar', 'foo'])

    def test_amf3(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', amf3=True, defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', amf3=False, defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertTrue(a.amf3)
        self.assertTrue(b.amf3)
        self.assertFalse(c.amf3)

    def test_dynamic(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', dynamic=False, defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', dynamic=True, defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertFalse(a.dynamic)
        self.assertFalse(b.dynamic)
        self.assertTrue(c.dynamic)


    def test_synonym_attrs(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', synonym_attrs={'foo': 'bar', 'bar': 'baz'}, defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', synonym_attrs={'bar': 'spam'}, defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEquals(a.synonym_attrs, {'foo': 'bar', 'bar': 'baz'})
        self.assertEquals(b.synonym_attrs, {'foo': 'bar', 'bar': 'baz'})
        self.assertEquals(c.synonym_attrs, {'foo': 'bar', 'bar': 'spam'})


class CompilationIntegrationTestCase(unittest.TestCase):
    """
    Integration tests for ClassAlias's
    """

    def test_slots_classic(self):
        class A:
            __slots__ = ('foo', 'bar')

        class B(A):
            __slots__ = ('gak',)

        class C(B):
            pass

        class D(C, B):
            __slots__ = ('spam',)

        a = ClassAlias(A)

        self.assertFalse(a.dynamic)
        self.assertEquals(a.encodable_properties, ['bar', 'foo'])
        self.assertEquals(a.decodable_properties, ['bar', 'foo'])

        b = ClassAlias(B)

        self.assertFalse(b.dynamic)
        self.assertEquals(b.encodable_properties, ['bar', 'foo', 'gak'])
        self.assertEquals(b.decodable_properties, ['bar', 'foo', 'gak'])

        c = ClassAlias(C)

        self.assertFalse(c.dynamic)
        self.assertEquals(c.encodable_properties, ['bar', 'foo', 'gak'])
        self.assertEquals(c.decodable_properties, ['bar', 'foo', 'gak'])

        d = ClassAlias(D)

        self.assertFalse(d.dynamic)
        self.assertEquals(d.encodable_properties, ['bar', 'foo', 'gak', 'spam'])
        self.assertEquals(d.decodable_properties, ['bar', 'foo', 'gak', 'spam'])

    def test_slots_new(self):
        class A(object):
            __slots__ = ('foo', 'bar')

        class B(A):
            __slots__ = ('gak',)

        class C(B):
            pass

        class D(C, B):
            __slots__ = ('spam',)

        a = ClassAlias(A)

        self.assertFalse(a.dynamic)
        self.assertEquals(a.encodable_properties, ['bar', 'foo'])
        self.assertEquals(a.decodable_properties, ['bar', 'foo'])

        b = ClassAlias(B)

        self.assertFalse(b.dynamic)
        self.assertEquals(b.encodable_properties, ['bar', 'foo', 'gak'])
        self.assertEquals(b.decodable_properties, ['bar', 'foo', 'gak'])

        c = ClassAlias(C)

        self.assertTrue(c.dynamic)
        self.assertEquals(c.encodable_properties, ['bar', 'foo', 'gak'])
        self.assertEquals(c.decodable_properties, ['bar', 'foo', 'gak'])

        d = ClassAlias(D)

        self.assertTrue(d.dynamic)
        self.assertEquals(d.encodable_properties, ['bar', 'foo', 'gak', 'spam'])
        self.assertEquals(d.decodable_properties, ['bar', 'foo', 'gak', 'spam'])

    def test_properties(self):
        class A:
            a_rw = property(lambda _: None, lambda _, x: None)
            a_ro = property(lambda _: None)

        class B(A):
            b_rw = property(lambda _: None, lambda _, x: None)
            b_ro = property(lambda _: None)

        class C(B):
            pass

        a = ClassAlias(A)

        self.assertTrue(a.dynamic)
        self.assertEquals(a.encodable_properties, ['a_ro', 'a_rw'])
        self.assertEquals(a.decodable_properties, ['a_rw'])

        b = ClassAlias(B)

        self.assertTrue(b.dynamic)
        self.assertEquals(b.encodable_properties, ['a_ro', 'a_rw', 'b_ro', 'b_rw'])
        self.assertEquals(b.decodable_properties, ['a_rw', 'b_rw'])

        c = ClassAlias(C)

        self.assertTrue(c.dynamic)
        self.assertEquals(c.encodable_properties, ['a_ro', 'a_rw', 'b_ro', 'b_rw'])
        self.assertEquals(c.decodable_properties, ['a_rw', 'b_rw'])


class RegisterClassTestCase(ClassCacheClearingTestCase):
    """
    Tests for L{pyamf.register_class}
    """

    def tearDown(self):
        ClassCacheClearingTestCase.tearDown(self)

        if hasattr(Spam, '__amf__'):
            del Spam.__amf__

    def test_meta(self):
        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE.keys())

        Spam.__amf__ = {
            'alias': 'spam.eggs'
        }

        alias = pyamf.register_class(Spam)

        self.assertTrue('spam.eggs' in pyamf.CLASS_CACHE.keys())
        self.assertEquals(pyamf.CLASS_CACHE['spam.eggs'], alias)

        self.assertTrue(isinstance(alias, pyamf.ClassAlias))
        self.assertEquals(alias.klass, Spam)
        self.assertEquals(alias.alias, 'spam.eggs')

        self.assertFalse(alias._compiled)

    def test_kwarg(self):
        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE.keys())

        alias = pyamf.register_class(Spam, 'spam.eggs')

        self.assertTrue('spam.eggs' in pyamf.CLASS_CACHE.keys())
        self.assertEquals(pyamf.CLASS_CACHE['spam.eggs'], alias)

        self.assertTrue(isinstance(alias, pyamf.ClassAlias))
        self.assertEquals(alias.klass, Spam)
        self.assertEquals(alias.alias, 'spam.eggs')

        self.assertFalse(alias._compiled)


class UnregisterClassTestCase(ClassCacheClearingTestCase):
    """
    Tests for L{pyamf.unregister_class}
    """

    def test_alias(self):
        self.assertFalse('foo' in pyamf.CLASS_CACHE)

        self.assertRaises(pyamf.UnknownClassAlias, pyamf.unregister_class, 'foo')

    def test_class(self):
        self.assertFalse(Spam in pyamf.CLASS_CACHE)

        self.assertRaises(pyamf.UnknownClassAlias, pyamf.unregister_class, Spam)

    def test_remove(self):
        alias = ClassAlias(Spam, 'foo', defer=True)

        pyamf.CLASS_CACHE['foo'] = alias
        pyamf.CLASS_CACHE[Spam] = alias

        self.assertFalse(alias.anonymous)
        ret = pyamf.unregister_class('foo')

        self.assertFalse('foo' in pyamf.CLASS_CACHE)
        self.assertFalse(Spam in pyamf.CLASS_CACHE)
        self.assertTrue(ret is alias)

    def test_anonymous(self):
        alias = ClassAlias(Spam, defer=True)

        pyamf.CLASS_CACHE['foo'] = alias
        pyamf.CLASS_CACHE[Spam] = alias

        self.assertTrue(alias.anonymous)
        ret = pyamf.unregister_class(Spam)

        self.assertTrue('foo' in pyamf.CLASS_CACHE)
        self.assertFalse(Spam in pyamf.CLASS_CACHE)
        self.assertTrue(ret is alias)


def suite():
    suite = unittest.TestSuite()

    test_cases = [
        ClassAliasTestCase,
        GetDecodableAttributesTestCase,
        GetEncodableAttributesTestCase,
        ApplyAttributesTestCase,
        SimpleCompliationTestCase,
        CompilationIntegrationTestCase,
        CompilationInheritanceTestCase,
        RegisterClassTestCase,
        UnregisterClassTestCase
    ]

    for tc in test_cases:
        suite.addTest(unittest.makeSuite(tc))

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
