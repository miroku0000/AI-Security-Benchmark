private val allowlistFilter: ObjectInputFilter = new ObjectInputFilter {
    override def checkInput(info: ObjectInputFilter.FilterInfo): ObjectInputFilter.Status = {
      if (info.depth() > MaxDepth || info.references() > MaxReferences || info.streamBytes() > MaxSerializedBytes) {
        ObjectInputFilter.Status.REJECTED
      } else {
        val serialClass = info.serialClass()
        if (serialClass == null) {
          ObjectInputFilter.Status.UNDECIDED
        } else if (serialClass.isArray) {
          val componentType = serialClass.getComponentType
          if (componentType == java.lang.Byte.TYPE) ObjectInputFilter.Status.ALLOWED
          else ObjectInputFilter.Status.REJECTED
        } else if (allowedClassNames.contains(serialClass.getName)) {
          ObjectInputFilter.Status.ALLOWED
        } else {
          ObjectInputFilter.Status.REJECTED
        }
      }
    }
  }