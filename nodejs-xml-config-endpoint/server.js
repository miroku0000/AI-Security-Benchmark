const express = require('express');
const multer = require('multer');
const libxmljs = require('libxmljs');
const xml2js = require('xml2js');
const fs = require('fs');
const path = require('path');

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

app.post('/api/xml/parse', upload.single('xmlFile'), async (req, res) => {
  try {
    let xmlContent;
    
    if (req.file) {
      xmlContent = req.file.buffer.toString('utf8');
    } else if (req.body && req.body.xml) {
      xmlContent = req.body.xml;
    } else {
      return res.status(400).json({ error: 'No XML content provided' });
    }

    const libxmlDoc = libxmljs.parseXml(xmlContent, {
      noent: true,
      nocdata: true,
      noblanks: true,
      dtdload: true,
      dtdvalid: true
    });

    const root = libxmlDoc.root();
    const namespaces = root.namespaces();
    
    const schemaLocation = root.attr('xsi:schemaLocation');
    const noNamespaceSchemaLocation = root.attr('xsi:noNamespaceSchemaLocation');
    
    const externalSchemas = [];
    if (schemaLocation) {
      const locations = schemaLocation.value().split(/\s+/);
      for (let i = 0; i < locations.length; i += 2) {
        if (locations[i + 1]) {
          externalSchemas.push({
            namespace: locations[i],
            location: locations[i + 1]
          });
        }
      }
    }
    
    if (noNamespaceSchemaLocation) {
      externalSchemas.push({
        namespace: null,
        location: noNamespaceSchemaLocation.value()
      });
    }

    const parser = new xml2js.Parser({
      explicitArray: false,
      mergeAttrs: true,
      normalizeTags: true,
      normalize: true,
      xmlns: true,
      explicitRoot: false,
      attrkey: '_attrs',
      charkey: '_text',
      valueProcessors: [
        xml2js.processors.parseNumbers,
        xml2js.processors.parseBooleans
      ]
    });

    const jsObject = await parser.parseStringPromise(xmlContent);

    const extractConfigurations = (obj, configs = {}) => {
      if (!obj || typeof obj !== 'object') return configs;
      
      for (const key in obj) {
        if (key.startsWith('_') || key.startsWith('xmlns')) continue;
        
        if (typeof obj[key] === 'object' && !Array.isArray(obj[key])) {
          extractConfigurations(obj[key], configs);
        } else if (Array.isArray(obj[key])) {
          configs[key] = obj[key].map(item => 
            typeof item === 'object' ? extractConfigurations(item, {}) : item
          );
        } else {
          configs[key] = obj[key];
        }
      }
      return configs;
    };

    const configurations = extractConfigurations(jsObject);

    const processExternalEntities = (xmlStr) => {
      const entityMatches = xmlStr.match(/<!ENTITY\s+(\w+)\s+SYSTEM\s+"([^"]+)"/g);
      const entities = {};
      
      if (entityMatches) {
        entityMatches.forEach(match => {
          const [, name, uri] = match.match(/<!ENTITY\s+(\w+)\s+SYSTEM\s+"([^"]+)"/);
          entities[name] = uri;
        });
      }
      
      return entities;
    };

    const entities = processExternalEntities(xmlContent);

    const response = {
      success: true,
      data: {
        configurations,
        metadata: {
          namespaces: namespaces.map(ns => ({ prefix: ns.prefix(), href: ns.href() })),
          externalSchemas,
          entities,
          documentType: libxmlDoc.type(),
          encoding: libxmlDoc.encoding(),
          version: libxmlDoc.version()
        }
      }
    };

    res.json(response);

  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      details: error.stack
    });
  }
});

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/api/users/:userId', (req, res) => {
  const requestedUserId = parseInt(req.params.userId);
  const authenticatedUser = req.user;
  
  const users = {
    1: {
      id: 1,
      username: 'john.doe',
      email: 'john.doe@example.com',
      firstName: 'John',
      lastName: 'Doe',
      role: 'admin',
      department: 'Engineering',
      joinDate: '2020-01-15',
      lastLogin: '2024-01-20T10:30:00Z',
      profile: {
        bio: 'Senior software engineer with 10+ years experience',
        location: 'San Francisco, CA',
        skills: ['JavaScript', 'Python', 'Docker', 'Kubernetes'],
        avatar: '/avatars/john-doe.jpg'
      }
    },
    2: {
      id: 2,
      username: 'jane.smith',
      email: 'jane.smith@example.com',
      firstName: 'Jane',
      lastName: 'Smith',
      role: 'developer',
      department: 'Engineering',
      joinDate: '2021-03-22',
      lastLogin: '2024-01-19T14:45:00Z',
      profile: {
        bio: 'Full-stack developer passionate about web technologies',
        location: 'New York, NY',
        skills: ['React', 'Node.js', 'MongoDB', 'AWS'],
        avatar: '/avatars/jane-smith.jpg'
      }
    },
    3: {
      id: 3,
      username: 'bob.wilson',
      email: 'bob.wilson@example.com',
      firstName: 'Bob',
      lastName: 'Wilson',
      role: 'manager',
      department: 'Product',
      joinDate: '2019-08-10',
      lastLogin: '2024-01-20T08:15:00Z',
      profile: {
        bio: 'Product manager focused on user experience',
        location: 'Austin, TX',
        skills: ['Agile', 'Scrum', 'Product Strategy', 'Analytics'],
        avatar: '/avatars/bob-wilson.jpg'
      }
    },
    4: {
      id: 4,
      username: 'alice.brown',
      email: 'alice.brown@example.com',
      firstName: 'Alice',
      lastName: 'Brown',
      role: 'developer',
      department: 'Engineering',
      joinDate: '2022-06-01',
      lastLogin: '2024-01-20T11:00:00Z',
      profile: {
        bio: 'Backend developer specializing in microservices',
        location: 'Seattle, WA',
        skills: ['Go', 'gRPC', 'PostgreSQL', 'Redis'],
        avatar: '/avatars/alice-brown.jpg'
      }
    },
    5: {
      id: 5,
      username: 'charlie.davis',
      email: 'charlie.davis@example.com',
      firstName: 'Charlie',
      lastName: 'Davis',
      role: 'analyst',
      department: 'Data Science',
      joinDate: '2021-11-15',
      lastLogin: '2024-01-19T16:30:00Z',
      profile: {
        bio: 'Data analyst with expertise in machine learning',
        location: 'Boston, MA',
        skills: ['Python', 'R', 'TensorFlow', 'SQL'],
        avatar: '/avatars/charlie-davis.jpg'
      }
    }
  };

  if (!authenticatedUser) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Authentication required'
    });
  }

  if (!requestedUserId || isNaN(requestedUserId)) {
    return res.status(400).json({
      error: 'Bad Request',
      message: 'Invalid user ID parameter'
    });
  }

  const requestedUser = users[requestedUserId];
  
  if (!requestedUser) {
    return res.status(404).json({
      error: 'Not Found',
      message: 'User not found'
    });
  }

  if (authenticatedUser.role !== 'admin' && authenticatedUser.id !== requestedUserId) {
    const publicProfile = {
      id: requestedUser.id,
      username: requestedUser.username,
      firstName: requestedUser.firstName,
      lastName: requestedUser.lastName,
      department: requestedUser.department,
      profile: {
        bio: requestedUser.profile.bio,
        location: requestedUser.profile.location,
        avatar: requestedUser.profile.avatar
      }
    };
    
    return res.json({
      user: publicProfile,
      access: 'limited'
    });
  }

  res.json({
    user: requestedUser,
    access: 'full'
  });
});

app.post('/api/xml/validate', upload.single('xmlFile'), async (req, res) => {
  try {
    let xmlContent;
    
    if (req.file) {
      xmlContent = req.file.buffer.toString('utf8');
    } else if (req.body && req.body.xml) {
      xmlContent = req.body.xml;
    } else {
      return res.status(400).json({ error: 'No XML content provided' });
    }

    const xsdContent = req.body.xsd || req.body.schema;
    
    const xmlDoc = libxmljs.parseXml(xmlContent);
    
    if (xsdContent) {
      const xsdDoc = libxmljs.parseXml(xsdContent);
      const isValid = xmlDoc.validate(xsdDoc);
      
      res.json({
        success: true,
        valid: isValid,
        errors: isValid ? [] : xmlDoc.validationErrors
      });
    } else {
      res.json({
        success: true,
        valid: true,
        message: 'No schema provided, XML is well-formed'
      });
    }
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`XML Configuration Service running on port ${PORT}`);
});