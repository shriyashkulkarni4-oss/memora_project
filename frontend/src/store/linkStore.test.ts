import { describe, expect, it } from 'vitest'

import { LinkSource } from '../types'
import { useLinkStore } from './linkStore'

describe('link store baseline', () => {
  it('creates an item and resolves edited tag names to tag records', () => {
    const created = useLinkStore.getState().addLink({
      title: 'Baseline item',
      source: LinkSource.MANUAL,
      tags: ['baseline'],
    })

    useLinkStore.getState().updateLink(created.id, { tags: ['updated'] })

    const item = useLinkStore.getState().links.find(link => link.id === created.id)
    expect(item?.tags.map(tag => tag.name)).toEqual(['updated'])
  })
})
